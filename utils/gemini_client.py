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

# Retry settings for rate limits and server availability
MAX_RETRIES = 5
DEFAULT_BACKOFF_SECONDS = 3.0


def _is_transient_error(err_str: str) -> bool:
    """Check if an error string indicates a rate-limit, quota exhaustion, 503 unavailable, or temporary server overload."""
    err_lower = err_str.lower()
    keywords = [
        "429", "resource_exhausted", "quota",
        "503", "unavailable", "high demand", "spikes in demand",
        "overloaded", "500", "502", "504", "deadline_exceeded",
        "temporarily unavailable", "try again later"
    ]
    return any(kw in err_lower for kw in keywords)


def _parse_retry_delay(err_str: str, attempt: int = 0) -> float:
    """Try to extract the server-suggested wait time from the error message.
    Falls back to exponential backoff if not parseable."""
    match = re.search(r"retry\s+in\s+(\d+)\s*s", err_str, re.IGNORECASE)
    if match:
        return float(match.group(1)) + 1.5
    return min(DEFAULT_BACKOFF_SECONDS * (1.8 ** attempt), 12.0)


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

    def _get_candidate_models(self) -> list[str]:
        models = [self.model_name, "gemini-3.6-flash", "gemini-2.5-flash"]
        candidates = []
        for m in models:
            if m and m not in candidates:
                candidates.append(m)
        return candidates

    def generate_json(self, prompt_or_contents, schema_class=None) -> dict:
        """
        Sends a prompt or list of contents to Gemini requesting a JSON output.
        Retries on transient 503/429 errors and falls back to alternate models.
        """
        if not self.client:
            raise ValueError("Gemini Client is not initialized. Please check API keys.")

        candidate_models = self._get_candidate_models()
        last_exception = None

        for model in candidate_models:
            for attempt in range(MAX_RETRIES):
                try:
                    config_args = {"response_mime_type": "application/json"}
                    if schema_class:
                        config_args["response_schema"] = schema_class

                    config = types.GenerateContentConfig(**config_args)
                    
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt_or_contents,
                        config=config
                    )
                    
                    text = response.text.strip()
                    if text.startswith("```json"):
                        text = text[7:]
                    if text.endswith("```"):
                        text = text[:-3]
                    text = text.strip()
                    
                    return json.loads(text)
                except Exception as e:
                    last_exception = e
                    err_str = str(e)

                    if _is_transient_error(err_str) and attempt < MAX_RETRIES - 1:
                        wait = _parse_retry_delay(err_str, attempt=attempt)
                        logger.warning(
                            f"Transient error on model '{model}' (attempt {attempt+1}/{MAX_RETRIES}): {e}. "
                            f"Retrying in {wait:.1f}s..."
                        )
                        time.sleep(wait)
                        continue
                    elif _is_transient_error(err_str):
                        logger.warning(f"Model '{model}' exhausted retries due to transient error. Trying next fallback model...")
                        break
                    else:
                        # Non-transient error: attempt fallback without schema config
                        try:
                            if isinstance(prompt_or_contents, list):
                                fallback_contents = prompt_or_contents + [" (Respond ONLY with a valid JSON block)"]
                            else:
                                fallback_contents = str(prompt_or_contents) + " (Respond ONLY with a valid JSON block)"
                                
                            response = self.client.models.generate_content(
                                model=model,
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
                            logger.error(f"Fallback generation failed: {fallback_err}")
                        raise e

        if last_exception:
            raise last_exception

    def generate(self, prompt: str) -> str:
        """
        Sends a prompt to Gemini requesting plain text output.
        """
        if not self.client:
            raise ValueError("Gemini Client is not initialized. Please check API keys.")

        candidate_models = self._get_candidate_models()
        last_exception = None

        for model in candidate_models:
            for attempt in range(MAX_RETRIES):
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt
                    )
                    return response.text.strip()
                except Exception as e:
                    last_exception = e
                    err_str = str(e)
                    if _is_transient_error(err_str) and attempt < MAX_RETRIES - 1:
                        wait = _parse_retry_delay(err_str, attempt=attempt)
                        logger.warning(
                            f"Transient error on model '{model}' (attempt {attempt+1}/{MAX_RETRIES}): {e}. "
                            f"Retrying in {wait:.1f}s..."
                        )
                        time.sleep(wait)
                        continue
                    elif _is_transient_error(err_str):
                        logger.warning(f"Model '{model}' failed. Trying next model...")
                        break
                    else:
                        raise e

        if last_exception:
            raise last_exception

# Single shared instance
gemini_client = GeminiClient()
