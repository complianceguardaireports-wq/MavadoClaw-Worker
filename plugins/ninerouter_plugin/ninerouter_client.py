"""
9Router Client - Backup AI Gateway Plugin
Provides failover routing and network intelligence
"""
import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

from plugins.omniroute_plugin.omniroute_client import OmniRouteClient, OmniRouteConfig


@dataclass
class NineRouterConfig:
    base_url: str = "http://9router:8081"
    omniroute_url: str = "http://omniroute:3000"
    timeout: int = 120
    api_key: str = "local-autonomous-key"
    health_check_interval: int = 30


class NineRouterClient:
    """Client for 9Router - backup LLM gateway."""

    def __init__(self, config: NineRouterConfig = None):
        self.config = config or NineRouterConfig()
        self._session = None

    async def initialize(self):
        if HAS_AIOHTTP:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            )

    async def chat_completion(self, messages: List[Dict], model: str = "auto",
                              temperature: float = 0.7, max_tokens: int = 4096) -> Any:
        payload = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
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
                return await resp.json()
        raise RuntimeError("9Router client not initialized")

    async def health_check(self) -> Dict[str, Any]:
        if self._session:
            try:
                async with self._session.get(
                    f"{self.config.base_url}/health"
                ) as resp:
                    return await resp.json()
            except Exception:
                return {"status": "down"}
        return {"status": "unavailable"}

    async def list_models(self) -> List[Dict]:
        if self._session:
            try:
                async with self._session.get(
                    f"{self.config.base_url}/v1/models"
                ) as resp:
                    data = await resp.json()
                    return data.get("data", [])
            except Exception:
                return []
        return []

    async def close(self):
        if self._session:
            await self._session.close()


class NineRouterFailoverManager:
    """Manages failover between OmniRoute and 9Router."""

    def __init__(self, omniroute_url: str = "http://omniroute:3000",
                 ninerouter_url: str = "http://9router:8081",
                 api_key: str = "local-autonomous-key"):
        self.omniroute = OmniRouteClient(
            OmniRouteConfig(base_url=omniroute_url, api_key=api_key)
        )
        self.ninerouter = NineRouterClient(
            NineRouterConfig(base_url=ninerouter_url, omniroute_url=omniroute_url, api_key=api_key)
        )
        self._initialized = False
        self.stats = {"primary": 0, "backup": 0, "failovers": 0, "errors": 0}

    async def _ensure_initialized(self):
        if not self._initialized:
            await self.omniroute.initialize()
            await self.ninerouter.initialize()
            self._initialized = True

    async def chat_completion(self, messages: List[Dict], model: str = "auto",
                              temperature: float = 0.7, max_tokens: int = 4096) -> Any:
        await self._ensure_initialized()

        try:
            result = await self.omniroute.chat_completion(
                messages, model, temperature, max_tokens
            )
            self.stats["primary"] += 1
            return result
        except Exception as exc:
            self.stats["failovers"] += 1
            print(f"[9Router] OmniRoute failed: {exc}, trying 9Router...")

        try:
            result = await self.ninerouter.chat_completion(
                messages, model, temperature, max_tokens
            )
            self.stats["backup"] += 1
            return result
        except Exception as exc:
            self.stats["errors"] += 1
            raise Exception(f"All providers failed. OmniRoute and 9Router both down.") from exc

    async def get_status(self) -> Dict[str, Any]:
        await self._ensure_initialized()
        omniroute_ok = False
        ninerouter_ok = False
        try:
            status = await self.omniroute.health_check()
            omniroute_ok = status.get("status") == "ok"
        except Exception:
            pass
        try:
            status = await self.ninerouter.health_check()
            ninerouter_ok = status.get("status") == "ok"
        except Exception:
            pass

        return {
            "omniroute": "healthy" if omniroute_ok else "down",
            "ninerouter": "healthy" if ninerouter_ok else "down",
            "stats": self.stats,
        }

    async def close(self):
        await self.omniroute.close()
        await self.ninerouter.close()
        self._initialized = False
