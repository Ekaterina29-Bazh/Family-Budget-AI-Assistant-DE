# test_gemini.py

import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.environ.get("GOOGLE_API_KEY")
print(f"GOOGLE_API_KEY exists: {api_key is not None}")
if api_key:
    print(f"Key preview: {api_key[:10]}...")

model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
print(f"Using model: {model_name}")

try:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_name,
        contents="Hello, this is a test. Reply with 'OK' if you receive this."
    )
    print("Gemini response success!")
    print(f"Response: {response.text.strip()}")
except Exception as e:
    print(f"Gemini call failed with error: {e}")
