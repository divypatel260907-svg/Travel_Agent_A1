"""
Shared LLM client factory.

Provides:
  - get_groq_llm()   → LangChain ChatGroq  (fast, streaming, tool-calling)
  - get_gemini_llm() → LangChain ChatGoogleGenerativeAI (complex reasoning)

Environment variables used:
  GROQ_API_KEY
  GEMINI_API_KEY
  GROQ_MODEL     (default: openai/gpt-oss-120b)
  GEMINI_MODEL   (default: gemini-2.5-flash)
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

_GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")


class _GroqClientWrapper:
    """Fallback LLM wrapper around official groq.Groq when langchain_groq is not installed."""
    def __init__(self, api_key: str, model: str, temperature: float = 0.2):
        from groq import Groq
        self.client = Groq(api_key=api_key)
        self.model = model
        self.temperature = temperature

    async def ainvoke(self, messages: list):
        std_messages = []
        for m in messages:
            if hasattr(m, "content"):
                role = "system" if getattr(m, "type", "") == "system" else "user"
                std_messages.append({"role": role, "content": m.content})
            elif isinstance(m, dict):
                std_messages.append(m)
            else:
                std_messages.append({"role": "user", "content": str(m)})

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=std_messages,
            temperature=self.temperature,
        )
        content = completion.choices[0].message.content or ""

        class _Response:
            def __init__(self, c):
                self.content = c

        return _Response(content)


@lru_cache(maxsize=1)
def get_groq_llm(temperature: float = 0.2):
    """
    Return a cached ChatGroq instance, with seamless fallback to official Groq SDK.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is not set. Add it to your .env file. "
            "Get a free key at https://console.groq.com"
        )
    try:
        from langchain_groq import ChatGroq  # noqa: PLC0415
        return ChatGroq(
            model=_GROQ_MODEL,
            api_key=api_key,
            temperature=temperature,
            max_retries=2,
        )
    except ModuleNotFoundError:
        return _GroqClientWrapper(api_key=api_key, model=_GROQ_MODEL, temperature=temperature)


@lru_cache(maxsize=1)
def get_gemini_llm(temperature: float = 0.4):
    """
    Return a cached ChatGoogleGenerativeAI instance.

    Preferred for:
    - Complex multi-step reasoning (Itinerary Builder, Contingency Agent)
    - Multi-language output
    - Larger context windows

    Args:
        temperature: Sampling temperature (0.0–1.0).

    Returns:
        langchain_google_genai.ChatGoogleGenerativeAI instance.

    Raises:
        ValueError: If GEMINI_API_KEY is not set.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Add it to your .env file. "
            "Get a free key at https://aistudio.google.com/app/apikey"
        )
    from langchain_google_genai import ChatGoogleGenerativeAI  # noqa: PLC0415

    return ChatGoogleGenerativeAI(
        model=_GEMINI_MODEL,
        google_api_key=api_key,
        temperature=temperature,
        max_retries=2,
    )
