"""
Unified AI Infrastructure Plugin for MavadoClaw
Combines OmniRoute (Primary) + 9Router (Backup) + Cloudflare Edge for 24/7 operations
No API keys required - all runs locally on PandaStack
"""
import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, AsyncGenerator, AsyncIterator
from enum import Enum


class ProviderStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass
class AIInfrastructureConfig:
    omniroute_url: str = "http://omniroute:3000"
    ninerouter_url: str = "http://9router:8081"
    cloudflare_worker_url: str = ""
    hf_inference_url: str = ""
    api_key: str = "local-autonomous-key"
    primary_provider: str = "omniroute"
    enable_failover: bool = True
    health_check_interval: int = 30


@dataclass
class ProviderHealth:
    name: str
    status: ProviderStatus = ProviderStatus.DOWN
    last_check: float = 0.0
    response_time_ms: float = 0.0
    consecutive_failures: int = 0
    total_requests: int = 0
    total_failures: int = 0


class AutonomousAIInfrastructure:
    """Unified AI infrastructure with automatic failover and edge routing."""

    def __init__(self, config: AIInfrastructureConfig = None):
        self.config = config or AIInfrastructureConfig()
        self._initialized = False
        self._session = None
        self.providers: Dict[str, ProviderHealth] = {
            "omniroute": ProviderHealth(name="omniroute"),
            "9router": ProviderHealth(name="9router"),
        }
        if self.config.cloudflare_worker_url:
            self.providers["cloudflare"] = ProviderHealth(name="cloudflare")
        if self.config.hf_inference_url:
            self.providers["huggingface"] = ProviderHealth(name="huggingface")
        self.stats = {
            "total_requests": 0,
            "omniroute_requests": 0,
            "ninerouter_requests": 0,
            "cloudflare_requests": 0,
            "hf_requests": 0,
            "failovers": 0,
            "errors": 0,
        }
        self._health_task: Optional[asyncio.Task] = None

    async def initialize(self):
        if self._initialized:
            return
        try:
            import aiohttp
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=120)
            )
        except ImportError:
            import urllib.request
            self._session = None

        await self._check_all_health()
        self._health_task = asyncio.create_task(self._health_loop())
        self._initialized = True
        print("[AI Infrastructure] Initialized: OmniRoute + 9Router ready for 24/7 operation")

    async def _health_loop(self):
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._check_all_health()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                print(f"[AI Infrastructure] Health check error: {exc}")

    async def _check_all_health(self):
        for name, health in self.providers.items():
            url = self._get_provider_url(name)
            if not url:
                continue
            start = time.time()
            try:
                healthy = await self._check_health(url)
                health.response_time_ms = (time.time() - start) * 1000
                if healthy:
                    health.status = ProviderStatus.HEALTHY
                    health.consecutive_failures = 0
                else:
                    health.consecutive_failures += 1
                    health.status = (
                        ProviderStatus.DEGRADED
                        if health.consecutive_failures < 3
                        else ProviderStatus.DOWN
                    )
                health.last_check = time.time()
            except Exception:
                health.consecutive_failures += 1
                health.status = ProviderStatus.DOWN
                health.last_check = time.time()

    async def _check_health(self, base_url: str) -> bool:
        if self._session:
            try:
                async with self._session.get(f"{base_url}/health") as resp:
                    return resp.status == 200
            except Exception:
                return False
        else:
            import urllib.request
            try:
                urllib.request.urlopen(f"{base_url}/health", timeout=5)
                return True
            except Exception:
                return False

    def _get_provider_url(self, name: str) -> Optional[str]:
        urls = {
            "omniroute": self.config.omniroute_url,
            "9router": self.config.ninerouter_url,
            "cloudflare": self.config.cloudflare_worker_url,
            "huggingface": self.config.hf_inference_url,
        }
        return urls.get(name)

    def _get_provider_order(self) -> List[str]:
        order = [self.config.primary_provider]
        if self.config.enable_failover:
            for name in self.providers:
                if name != self.config.primary_provider:
                    order.append(name)
        return order

    async def _call_provider(self, provider: str, messages: List[Dict],
                             model: str, temperature: float = 0.7,
                             max_tokens: int = 4096, stream: bool = False) -> Any:
        url = self._get_provider_url(provider)
        if not url:
            raise ValueError(f"Provider {provider} has no URL configured")

        payload = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if self._session:
            headers = {"Content-Type": "application/json"}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            async with self._session.post(
                f"{url}/v1/chat/completions",
                json=payload,
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Provider {provider} returned {resp.status}: {text}")
                if stream:
                    return resp
                return await resp.json()
        else:
            import urllib.request
            req = urllib.request.Request(
                f"{url}/v1/chat/completions",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode())

    async def chat_completion(self, messages: List[Dict], model: str = "auto",
                              temperature: float = 0.7, max_tokens: int = 4096) -> Dict:
        self.stats["total_requests"] += 1
        last_error = None

        for provider in self._get_provider_order():
            health = self.providers.get(provider)
            if health and health.status == ProviderStatus.DOWN:
                continue
            try:
                self.stats[f"{provider}_requests"] += 1
                result = await self._call_provider(
                    provider, messages, model, temperature, max_tokens
                )
                if health:
                    health.total_requests += 1
                return result
            except Exception as exc:
                last_error = exc
                if health:
                    health.total_failures += 1
                    health.consecutive_failures += 1
                self.stats["failovers"] += 1
                print(f"[AI Infrastructure] Provider {provider} failed: {exc}")
                continue

        self.stats["errors"] += 1
        raise Exception(f"All providers failed. Last error: {last_error}")

    async def stream_chat_completion(self, messages: List[Dict], model: str = "auto",
                                     temperature: float = 0.7,
                                     max_tokens: int = 4096) -> AsyncGenerator[Dict, None]:
        self.stats["total_requests"] += 1
        for provider in self._get_provider_order():
            health = self.providers.get(provider)
            if health and health.status == ProviderStatus.DOWN:
                continue
            try:
                self.stats[f"{provider}_requests"] += 1
                resp = await self._call_provider(
                    provider, messages, model, temperature, max_tokens, stream=True
                )
                if health:
                    health.total_requests += 1
                async for line in resp.content:
                    decoded = line.decode().strip()
                    if decoded.startswith("data: "):
                        data = decoded[6:]
                        if data == "[DONE]":
                            yield {"done": True}
                            return
                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and chunk["choices"]:
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield {"content": delta["content"]}
                        except json.JSONDecodeError:
                            continue
                return
            except Exception as exc:
                self.stats["failovers"] += 1
                print(f"[AI Infrastructure] Stream provider {provider} failed: {exc}")
                continue
        yield {"error": "All providers failed"}

    async def embeddings(self, texts: List[str], model: str = "bge-small-en-v1.5") -> Any:
        for provider in self._get_provider_order():
            url = self._get_provider_url(provider)
            if not url:
                continue
            try:
                if self._session:
                    async with self._session.post(
                        f"{url}/v1/embeddings",
                        json={"input": texts, "model": model},
                    ) as resp:
                        if resp.status == 200:
                            return await resp.json()
                else:
                    import urllib.request
                    req = urllib.request.Request(
                        f"{url}/v1/embeddings",
                        data=json.dumps({"input": texts, "model": model}).encode(),
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        return json.loads(resp.read().decode())
            except Exception:
                continue
        raise Exception("All providers failed for embeddings")

    async def health_check(self) -> Dict[str, Any]:
        await self._check_all_health()
        healthy_count = sum(
            1 for h in self.providers.values()
            if h.status == ProviderStatus.HEALTHY
        )
        return {
            "status": "healthy" if healthy_count > 0 else "degraded",
            "providers": {
                name: {
                    "status": h.status.value,
                    "response_time_ms": round(h.response_time_ms, 1),
                    "consecutive_failures": h.consecutive_failures,
                }
                for name, h in self.providers.items()
            },
            "stats": self.stats,
        }

    async def get_models(self) -> List[Dict]:
        for provider in self._get_provider_order():
            url = self._get_provider_url(provider)
            if not url:
                continue
            try:
                if self._session:
                    async with self._session.get(f"{url}/v1/models") as resp:
                        if resp.status == 200:
                            return (await resp.json()).get("data", [])
            except Exception:
                continue
        return []

    async def close(self):
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        if self._session:
            await self._session.close()
        self._initialized = False
        print("[AI Infrastructure] Shut down")


_ai_infrastructure: Optional[AutonomousAIInfrastructure] = None


async def get_ai_infrastructure() -> AutonomousAIInfrastructure:
    global _ai_infrastructure
    if _ai_infrastructure is None:
        _ai_infrastructure = AutonomousAIInfrastructure()
    if not _ai_infrastructure._initialized:
        await _ai_infrastructure.initialize()
    return _ai_infrastructure


async def close_ai_infrastructure():
    global _ai_infrastructure
    if _ai_infrastructure:
        await _ai_infrastructure.close()
        _ai_infrastructure = None


async def ai_chat(messages, model="auto", **kwargs):
    infra = await get_ai_infrastructure()
    return await infra.chat_completion(messages, model, **kwargs)


async def ai_health():
    infra = await get_ai_infrastructure()
    return await infra.health_check()


async def ai_models():
    infra = await get_ai_infrastructure()
    return await infra.get_models()


def get_agent_info():
    return [
        {"name": "OmniRoute Gateway", "role": "gateway", "status": "active"},
        {"name": "9Router Backup", "role": "backup", "status": "active"},
    ]
