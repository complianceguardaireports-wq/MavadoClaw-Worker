"""
Lightning AI Plugin
Manages model deployment and inference via Lightning.ai Studios and LitServe
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


@dataclass
class LightningConfig:
    api_key: str = ""
    studio_url: str = "https://lightning.ai"
    api_url: str = "https://api.lightning.ai"


class LightningClient:
    """Client for Lightning AI Studios and LitServe deployment."""

    def __init__(self, config: LightningConfig = None):
        self.config = config or LightningConfig()
        self._session = None

    async def initialize(self):
        if HAS_AIOHTTP:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60),
                headers={"Authorization": f"Bearer {self.config.api_key}"},
            )

    async def list_studios(self) -> List[Dict]:
        if self._session:
            async with self._session.get(
                f"{self.config.api_url}/v1/studios"
            ) as resp:
                return await resp.json()
        return []

    async def get_credits(self) -> Dict[str, Any]:
        if self._session:
            async with self._session.get(
                f"{self.config.api_url}/v1/credits"
            ) as resp:
                return await resp.json()
        return {"credits": 0}

    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "configured" if self.config.api_key else "not_configured",
            "features": [
                "GPU Studios (A100, H100, H200)",
                "LitServe inference",
                "Auto-sleep GPUs",
                "15 free credits/month",
            ],
        }

    async def close(self):
        if self._session:
            await self._session.close()


def get_agent_info():
    return {
        "name": "Lightning AI Agent",
        "role": "gpu",
        "status": "active",
        "description": "GPU compute and model fine-tuning via Lightning.ai",
    }
