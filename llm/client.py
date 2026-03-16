import httpx
from typing import Optional

from core.logger import get_logger

log = get_logger("llm.client")


class LLMClient:
    def __init__(self):
        self.api_key: Optional[str] = None
        self.base_url: Optional[str] = None
        self.model: Optional[str] = None
        self._http: Optional[httpx.AsyncClient] = None

    def configure(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._http = httpx.AsyncClient(timeout=120.0)
        log.info(f"LLM configured: model={model}, base_url={self.base_url}")

    @property
    def is_configured(self) -> bool:
        return all([self.api_key, self.base_url, self.model, self._http])

    async def chat_with_vision(self, messages: list[dict], screenshot_b64: str, temperature: float = 0.2) -> str:
        """Call LLM with vision: injects the screenshot into the last user message."""
        if not self.is_configured:
            raise RuntimeError("LLM client not configured")

        enhanced = []
        for i, msg in enumerate(messages):
            if i == len(messages) - 1 and msg["role"] == "user":
                text = msg["content"] if isinstance(msg["content"], str) else ""
                enhanced.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{screenshot_b64}",
                                "detail": "high",
                            },
                        },
                    ],
                })
            else:
                enhanced.append(msg)

        return await self.chat(enhanced, temperature=temperature)

    async def chat(self, messages: list[dict], temperature: float = 0.2) -> str:
        if not self.is_configured:
            raise RuntimeError("LLM client not configured")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        log.debug(f"Calling LLM: {self.model} with {len(messages)} messages")

        try:
            resp = await self._http.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            log.info(f"LLM response received ({len(content)} chars)")
            return content
        except httpx.HTTPStatusError as e:
            log.error(f"LLM HTTP error: {e.response.status_code} - {e.response.text[:200]}")
            raise
        except Exception as e:
            log.error(f"LLM request failed: {e}")
            raise

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None
