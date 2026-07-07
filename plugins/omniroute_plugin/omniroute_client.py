"""
OmniRoute Client - Primary AI Gateway Plugin
Routes LLM requests through the OmniRoute Node.js service
"""
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, AsyncGenerator

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


@dataclass
class OmniRouteConfig:
    base_url: str = "http://omniroute:3000"
    timeout: int = 120
    api_key: str = "local-autonomous-key"


class OmniRouteClient:
    """Client for OmniRoute AI Gateway - primary LLM router."""

    def __init__(self, config: OmniRouteConfig = None):
        self.config = config or OmniRouteConfig()
        self._session = None
        self._client = None

    async def initialize(self):
        if HAS_AIOHTTP:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            )
        elif HAS_HTTPX:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
            )

    async def chat_completion(self, messages: List[Dict], model: str = "auto",
                              temperature: float = 0.7, max_tokens: int = 4096,
                              stream: bool = False) -> Any:
        payload = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

        if self._session:
            async with self._session.post(
                f"{self.config.base_url}/v1/chat/completions",
                json=payload,
                headers=headers,
            ) as resp:
                if stream:
                    return resp
                return await resp.json()
        elif self._client:
            resp = await self._client.post(
                "/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            return resp.json()
        else:
            raise RuntimeError("No HTTP client available. Install aiohttp or httpx.")

    async def stream_chat(self, messages: List[Dict], model: str = "auto",
                          **kwargs) -> AsyncGenerator[str, None]:
        resp = await self.chat_completion(messages, model, stream=True, **kwargs)
        if self._session:
            async for line in resp.content:
                decoded = line.decode().strip()
                if decoded.startswith("data: "):
                    data = decoded[6:]
                    if data == "[DONE]":
                        return
                    try:
                        chunk = json.loads(data)
                        if "choices" in chunk and chunk["choices"]:
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                    except json.JSONDecodeError:
                        continue

    async def health_check(self) -> Dict[str, Any]:
        if self._session:
            async with self._session.get(f"{self.config.base_url}/health") as resp:
                return await resp.json()
        elif self._client:
            resp = await self._client.get("/health")
            return resp.json()
        return {"status": "unavailable"}

    async def list_models(self) -> List[Dict]:
        if self._session:
            async with self._session.get(f"{self.config.base_url}/v1/models") as resp:
                data = await resp.json()
                return data.get("data", [])
        elif self._client:
            resp = await self._client.get("/v1/models")
            return resp.json().get("data", [])
        return []

    async def embeddings(self, texts: List[str], model: str = "text-embedding-ada-002") -> Any:
        payload = {"input": texts, "model": model}
        if self._session:
            async with self._session.post(
                f"{self.config.base_url}/v1/embeddings",
                json=payload,
            ) as resp:
                return await resp.json()
        elif self._client:
            resp = await self._client.post("/v1/embeddings", json=payload)
            return resp.json()
        return {}

    async def close(self):
        if self._session:
            await self._session.close()
        if self._client:
            await self._client.aclose()
