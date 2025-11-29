import os

from google import genai


def get_gemini_client() -> genai.Client:
    """
    Return a configured Gemini client.

    Expects:
    - GEMINI_API_KEY in environment
    - Optional: GEMINI_MODEL for default model name
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in environment")

    client = genai.Client(api_key=api_key)
    return client


def get_default_gemini_model() -> str:
    """Return the default Gemini model name, override via GEMINI_MODEL env var."""
    return os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


