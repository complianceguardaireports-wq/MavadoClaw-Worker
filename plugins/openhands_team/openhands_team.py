"""
OpenHands Team Plugin
Manages OpenHands coding agent delegation and task execution
"""
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


@dataclass
class OpenHandsConfig:
    base_url: str = "http://openhands:3001"
    timeout: int = 300
    workspace: str = "/workspace"


class OpenHandsTeam:
    """Manages OpenHands coding agent for software engineering tasks."""

    def __init__(self, config: OpenHandsConfig = None):
        self.config = config or OpenHandsConfig()
        self._session = None
        self.stats = {"tasks_assigned": 0, "tasks_completed": 0, "errors": 0}

    async def initialize(self):
        if HAS_AIOHTTP:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            )

    async def assign_task(self, task: str, context: Optional[Dict] = None) -> Dict:
        self.stats["tasks_assigned"] += 1
        payload = {
            "task": task,
            "context": context or {},
            "workspace": self.config.workspace,
        }
        if self._session:
            try:
                async with self._session.post(
                    f"{self.config.base_url}/api/execute",
                    json=payload,
                ) as resp:
                    result = await resp.json()
                    self.stats["tasks_completed"] += 1
                    return result
            except Exception as exc:
                self.stats["errors"] += 1
                return {"error": str(exc), "status": "failed"}
        return {"error": "OpenHands client not initialized", "status": "failed"}

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

    async def list_sessions(self) -> List[Dict]:
        if self._session:
            try:
                async with self._session.get(
                    f"{self.config.base_url}/api/sessions"
                ) as resp:
                    return (await resp.json()).get("sessions", [])
            except Exception:
                return []
        return []

    async def close(self):
        if self._session:
            await self._session.close()
