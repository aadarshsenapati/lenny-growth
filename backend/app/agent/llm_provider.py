"""
Flexible LLM configuration layer.

Swapping providers is a config change (LLM_PROVIDER=groq|ollama), never a
code change. Both providers implement the same `complete()` interface so the
rest of the app (skills, router) never needs to know which one is active.

- groq   : cloud provider, free tier, used as the default "cloud LLM" option.
- ollama : local provider, MANDATORY for the submitted demo per the
           assignment brief. If Ollama is unreachable we raise a typed error
           so the API can degrade gracefully (see core/exceptions.py) instead
           of hanging or crashing.
"""
import time
from typing import Protocol

import httpx
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.core.exceptions import LLMProviderUnavailableError, LLMTimeoutError
from app.logging_config import get_logger

log = get_logger(__name__)


class LLMResult:
    def __init__(self, text: str, provider: str, model: str, latency_ms: int):
        self.text = text
        self.provider = provider
        self.model = model
        self.latency_ms = latency_ms


class LLMClient(Protocol):
    async def complete(self, system: str, messages: list[dict], temperature: float = 0.3) -> LLMResult: ...
    async def is_reachable(self) -> bool: ...


class GroqClient:
    def __init__(self):
        settings = get_settings()
        self.model = settings.groq_model
        self.api_key = settings.groq_api_key
        self._client = None
        if self.api_key:
            from groq import AsyncGroq

            self._client = AsyncGroq(api_key=self.api_key)

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
        retry=retry_if_not_exception_type(LLMProviderUnavailableError),
    )
    async def complete(self, system: str, messages: list[dict], temperature: float = 0.3) -> LLMResult:
        if not self._client:
            raise LLMProviderUnavailableError("GROQ_API_KEY is not configured.")

        start = time.perf_counter()
        try:
            resp = await self._client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=[{"role": "system", "content": system}, *messages],
                timeout=30,
            )
        except Exception as exc:  # noqa: BLE001 - normalize all SDK errors
            log.error("groq_call_failed", error=str(exc))
            raise LLMProviderUnavailableError(f"Groq request failed: {exc}") from exc

        latency_ms = int((time.perf_counter() - start) * 1000)
        text = resp.choices[0].message.content or ""
        return LLMResult(text=text, provider="groq", model=self.model, latency_ms=latency_ms)

    async def is_reachable(self) -> bool:
        return self.api_key is not None


class OllamaClient:
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model

    async def complete(self, system: str, messages: list[dict], temperature: float = 0.3) -> LLMResult:
        start = time.perf_counter()
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, *messages],
            "stream": False,
            "options": {"temperature": temperature},
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
        except httpx.ConnectError as exc:
            raise LLMProviderUnavailableError(
                "Ollama is not reachable. Is `ollama serve` running and is the model pulled?"
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("Ollama request timed out.") from exc
        except httpx.HTTPStatusError as exc:
            raise LLMProviderUnavailableError(f"Ollama returned an error: {exc}") from exc

        latency_ms = int((time.perf_counter() - start) * 1000)
        data = resp.json()
        text = data.get("message", {}).get("content", "")
        return LLMResult(text=text, provider="ollama", model=self.model, latency_ms=latency_ms)

    async def is_reachable(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False


def get_llm_client(provider: str | None = None) -> LLMClient:
    """Factory used everywhere else in the app. `provider` lets a single
    request override the default configured in Settings (used by the UI
    toggle) without restarting the app."""
    settings = get_settings()
    resolved = provider or settings.llm_provider
    if resolved == "ollama":
        return OllamaClient()
    return GroqClient()