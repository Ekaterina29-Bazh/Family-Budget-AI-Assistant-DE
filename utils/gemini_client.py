# utils/gemini_client.py

import os
import re
import json
import time
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv(override=True)

# Map GOOGLE_API_KEY to GEMINI_API_KEY if needed by the SDK
if "GOOGLE_API_KEY" in os.environ:
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

# Disable Vertex AI default if not set
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "False")

logger = logging.getLogger(__name__)

# Retry settings for free-tier quota (20 req/min)
MAX_RETRIES = 4
DEFAULT_BACKOFF_SECONDS = 12.0  # Fallback if we can't parse the server's suggested delay


def _is_rate_limited(err_str: str) -> bool:
    """Check if an error string indicates a rate-limit / quota exhaustion."""
    return "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower()


def _parse_retry_delay(err_str: str) -> float:
    """Try to extract the server-suggested wait time from the error message.
    Falls back to DEFAULT_BACKOFF_SECONDS if not parseable."""
    # Matches patterns like "retry in 31s" or "Please retry in 45s"
    match = re.search(r"retry\s+in\s+(\d+)\s*s", err_str, re.IGNORECASE)
    if match:
        return float(match.group(1)) + 2.0  # add a small buffer
    return DEFAULT_BACKOFF_SECONDS


class GeminiClient:
    def __init__(self):
        self.api_key = None
        self.model_name = None
        
        try:
            import streamlit as st
            if hasattr(st, "secrets"):
                if "GEMINI_API_KEY" in st.secrets:
                    self.api_key = st.secrets["GEMINI_API_KEY"]
                elif "GOOGLE_API_KEY" in st.secrets:
                    self.api_key = st.secrets["GOOGLE_API_KEY"]
                
                if "GEMINI_MODEL" in st.secrets:
                    self.model_name = st.secrets["GEMINI_MODEL"]
        except Exception:
            pass

        if not self.api_key:
            self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.model_name:
            self.model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        
        if not self.api_key:
            logger.warning("GEMINI_API_KEY / GOOGLE_API_KEY not found in secrets or environment!")
            
        try:
            # Initialize the official google-genai Client
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Client: {e}")
            self.client = None

    def generate_json(self, prompt_or_contents, schema_class=None) -> dict:
        """
        Sends a prompt or list of contents to Gemini requesting a JSON output.
        Optionally takes a Pydantic schema class to enforce structure.
        """
        if not self.client:
            raise ValueError("Gemini Client is not initialized. Please check API keys.")

        for attempt in range(MAX_RETRIES):
            try:
                config_args = {"response_mime_type": "application/json"}
                if schema_class:
                    config_args["response_schema"] = schema_class

                config = types.GenerateContentConfig(**config_args)
                
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt_or_contents,
                    config=config
                )
                
                text = response.text.strip()
                # Clean possible markdown wrapping
                if text.startswith("```json"):
                     text = text[7:]
                if text.endswith("```"):
                     text = text[:-3]
                text = text.strip()
                
                return json.loads(text)
            except Exception as e:
                err_str = str(e)

                if _is_rate_limited(err_str) and attempt < MAX_RETRIES - 1:
                    wait = _parse_retry_delay(err_str)
                    logger.warning(
                        f"Rate limited by Gemini (attempt {attempt+1}/{MAX_RETRIES}). "
                        f"Waiting {wait:.0f}s before retry..."
                    )
                    time.sleep(wait)
                    continue
                
                logger.error(f"Error during Gemini JSON generation on attempt {attempt+1}: {e}")
                
                # Only attempt the unstructured fallback for NON-rate-limit errors,
                # otherwise we'd burn another quota slot for nothing.
                if not _is_rate_limited(err_str):
                    try:
                        if isinstance(prompt_or_contents, list):
                            fallback_contents = prompt_or_contents + [" (Respond ONLY with a valid JSON block)"]
                        else:
                            fallback_contents = str(prompt_or_contents) + " (Respond ONLY with a valid JSON block)"
                            
                        response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=fallback_contents
                        )
                        text = response.text.strip()
                        if text.startswith("```json"):
                            text = text[7:]
                        if text.endswith("```"):
                            text = text[:-3]
                        text = text.strip()
                        return json.loads(text)
                    except Exception as fallback_err:
                        logger.error(f"Fallback generation also failed: {fallback_err}")

                raise e

    def generate(self, prompt: str) -> str:
        """
        Sends a prompt to Gemini requesting plain text output.
        """
        if not self.client:
            raise ValueError("Gemini Client is not initialized. Please check API keys.")

        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                return response.text.strip()
            except Exception as e:
                err_str = str(e)
                if _is_rate_limited(err_str) and attempt < MAX_RETRIES - 1:
                    wait = _parse_retry_delay(err_str)
                    logger.warning(
                        f"Rate limited by Gemini (attempt {attempt+1}/{MAX_RETRIES}). "
                        f"Waiting {wait:.0f}s before retry..."
                    )
                    time.sleep(wait)
                    continue
                logger.error(f"Error during Gemini generation: {e}")
                raise e

# Single shared instance
gemini_client = GeminiClient()
