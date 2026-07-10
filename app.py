"""
MavadoClaw Worker - Main Entry Point
CEO/Orchestrator for the Autonomous AI Company
Runs on port 8080, supervisor.sh manages this process
"""
import os
import sys
import json
import signal
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
import uvicorn

BASE_DIR = Path(__file__).resolve().parent
PLUGIN_DIR = BASE_DIR / "plugins"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("mavado")


def load_config() -> dict:
    for name in ("config.json", "config.json.template"):
        path = BASE_DIR / name
        if path.exists():
            logger.info("Loading config from %s", path)
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    logger.warning("No config file found, using defaults")
    return {}


CONFIG = load_config()


_plugins: dict = {}


def _load_plugins():
    if not PLUGIN_DIR.is_dir():
        logger.warning("Plugin directory %s not found", PLUGIN_DIR)
        return

    for entry in PLUGIN_DIR.iterdir():
        if entry.is_dir() and (entry / "__init__.py").exists():
            pkg_name = entry.name
            try:
                mod = __import__(f"plugins.{pkg_name}", fromlist=[pkg_name])
                _plugins[pkg_name] = mod
                logger.info("Loaded plugin: %s", pkg_name)
            except Exception as exc:
                logger.warning("Failed to load plugin %s: %s", pkg_name, exc)

    for py_file in PLUGIN_DIR.glob("*.py"):
        if py_file.stem == "__init__":
            continue
        try:
            mod = __import__(f"plugins.{py_file.stem}", fromlist=[py_file.stem])
            _plugins[py_file.stem] = mod
            logger.info("Loaded plugin module: %s", py_file.stem)
        except Exception as exc:
            logger.warning("Failed to load plugin module %s: %s", py_file.stem, exc)


_ai_infra = None


async def _get_ai_infra():
    global _ai_infra
    if _ai_infra is not None:
        return _ai_infra
    try:
        from plugins.ai_infrastructure import (
            AutonomousAIInfrastructure,
            AIInfrastructureConfig,
        )
        plugin_cfg = CONFIG.get("plugin_config", {})
        omniroute_cfg = plugin_cfg.get("omniroute", {})
        ninerouter_cfg = plugin_cfg.get("ninerouter", {})

        cfg = AIInfrastructureConfig(
            omniroute_url=os.environ.get(
                "OMNIROUTE_URL", omniroute_cfg.get("base_url", "http://omniroute:3000")
            ),
            ninerouter_url=os.environ.get(
                "NINEROUTER_URL", ninerouter_cfg.get("base_url", "http://9router:8081")
            ),
            api_key=os.environ.get(
                "LOCAL_AUTONOMOUS_KEY", "local-autonomous-key"
            ),
            primary_provider="omniroute",
            enable_failover=ninerouter_cfg.get("fallback_enabled", True),
        )
        _ai_infra = AutonomousAIInfrastructure(cfg)
        await _ai_infra.initialize()
        logger.info("AI infrastructure initialized (OmniRoute + 9Router)")
    except Exception as exc:
        logger.error("AI infra init failed: %s", exc)
        _ai_infra = None
    return _ai_infra


async def _close_ai_infra():
    global _ai_infra
    if _ai_infra:
        try:
            await _ai_infra.close()
        except Exception:
            pass
        _ai_infra = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_plugins()
    logger.info("MavadoClaw starting on port %s", os.environ.get("PORT", "8080"))
    logger.info("Plugins loaded: %s", list(_plugins.keys()))
    try:
        await _get_ai_infra()
    except Exception:
        logger.warning("AI infra not ready yet (will retry on first request)")
    yield
    await _close_ai_infra()
    logger.info("MavadoClaw shut down")


app = FastAPI(
    title="MavadoClaw",
    description="CEO/Orchestrator for the Autonomous AI Company",
    version="2.0.0",
    lifespan=lifespan,
)


class ChatMessage(BaseModel):
    role: str = Field(..., description="system, user, or assistant")
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = False
    provider: str = "auto"


class TaskRequest(BaseModel):
    task: str
    agent: str = "auto"
    priority: int = 5
    context: Optional[Dict[str, Any]] = None


class DeployRequest(BaseModel):
    project: str
    platform: str = "huggingface"
    config: Optional[Dict[str, Any]] = None


@app.get("/health")
async def health():
    infra_status = "not_ready"
    infra_detail = {}
    infra = await _get_ai_infra()
    if infra:
        try:
            detail = await infra.health_check()
            infra_status = detail.get("status", "unknown")
            infra_detail = detail
        except Exception as exc:
            infra_status = "error"
            infra_detail = {"error": str(exc)}

    return {
        "status": "healthy",
        "service": "mavado",
        "version": "2.0.0",
        "plugins": list(_plugins.keys()),
        "ai_infrastructure": infra_status,
        "infra_detail": infra_detail,
        "endpoints": {
            "health": "/health",
            "chat": "/api/chat (POST)",
            "task": "/api/task (POST)",
            "deploy": "/api/deploy (POST)",
            "agents": "/api/agents (GET)",
            "status": "/api/status (GET)",
        },
    }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    for msg in request.messages:
        if msg.role not in ("system", "user", "assistant"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role: {msg.role}. Must be system, user, or assistant",
            )

    system_msg = CONFIG.get(
        "character_desc",
        "You are MavadoClaw, CEO of an autonomous AI Company.",
    )
    messages = [m.model_dump() for m in request.messages]
    if not any(m["role"] == "system" for m in messages):
        messages.insert(0, {"role": "system", "content": system_msg})

    model = request.model or CONFIG.get("model", "auto")
    temperature = request.temperature or CONFIG.get("temperature", 0.7)
    max_tokens = request.max_tokens or CONFIG.get("conversation_max_tokens", 4096)

    # Try primary AI infrastructure (OmniRoute / 9Router)
    infra = await _get_ai_infra()
    if infra:
        try:
            if request.stream:
                async def generate():
                    async for chunk in infra.stream_chat_completion(
                        messages, model, temperature=temperature, max_tokens=max_tokens
                    ):
                        yield json.dumps(chunk) + "\n"
                return StreamingResponse(generate(), media_type="application/x-ndjson")

            result = await infra.chat_completion(messages, model, temperature, max_tokens)
            return result
        except Exception as exc:
            logger.warning("Primary AI infra failed, trying free fallback: %s", exc)

    # Fallback: free HuggingFace inference (no API key needed)
    try:
        from plugins.free_inference import chat_completion as free_chat, is_available
        if is_available():
            logger.info("Using free inference fallback (HuggingFace)")
            result = await free_chat(messages, temperature=temperature, max_tokens=max_tokens)
            return result
    except Exception as exc:
        logger.error("Free inference fallback also failed: %s", exc)

    raise HTTPException(
        status_code=503,
        detail="AI infrastructure unavailable (all providers failed)",
    )


@app.post("/api/task")
async def execute_task(request: TaskRequest):
    task_context = request.context or {}
    task_context["task"] = request.task
    task_context["priority"] = request.priority

    if request.agent == "auto" or request.agent == "code":
        messages = [
            {"role": "system", "content": "You are a senior software engineer. Execute the given task with high quality code."},
            {"role": "user", "content": request.task},
        ]
    elif request.agent == "research":
        messages = [
            {"role": "system", "content": "You are a research analyst. Provide comprehensive, well-sourced research on the given topic."},
            {"role": "user", "content": request.task},
        ]
    elif request.agent == "marketing":
        messages = [
            {"role": "system", "content": "You are a marketing strategist. Create compelling marketing content and strategies."},
            {"role": "user", "content": request.task},
        ]
    else:
        messages = [
            {"role": "system", "content": f"You are a specialized AI agent. Execute: {request.task}"},
            {"role": "user", "content": request.task},
        ]

    # Try primary AI infra, then fallback
    infra = await _get_ai_infra()
    if infra:
        try:
            result = await infra.chat_completion(messages, "auto", 0.7, 4096)
            return {"status": "completed", "agent": request.agent, "task": request.task, "result": result}
        except Exception as exc:
            logger.warning("Primary AI infra failed for task, trying fallback: %s", exc)

    try:
        from plugins.free_inference import chat_completion as free_chat, is_available
        if is_available():
            result = await free_chat(messages, max_tokens=2048)
            return {"status": "completed (free)", "agent": request.agent, "task": request.task, "result": result}
    except Exception as exc:
        logger.error("Free inference fallback also failed: %s", exc)

    raise HTTPException(status_code=503, detail="AI infrastructure unavailable (all providers failed)")


@app.post("/api/deploy")
async def deploy(request: DeployRequest):
    if request.platform == "huggingface":
        return {
            "status": "deployment_initiated",
            "platform": "huggingface",
            "project": request.project,
            "instructions": "Push to GitHub and connect to HuggingFace Spaces",
        }
    elif request.platform == "cloudflare":
        return {
            "status": "deployment_initiated",
            "platform": "cloudflare",
            "project": request.project,
            "instructions": "Run: cd cloudflare-worker && npx wrangler deploy",
        }
    elif request.platform == "lightning":
        return {
            "status": "deployment_initiated",
            "platform": "lightning",
            "project": request.project,
            "instructions": "Upload to Lightning AI Studios via web UI or CLI",
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {request.platform}")


@app.get("/api/agents")
async def list_agents():
    agents = [
        {
            "name": "MavadoClaw CEO",
            "role": "ceo",
            "status": "active",
            "description": "Main orchestrator and CEO of the AI company",
        },
        {
            "name": "OmniRoute Gateway",
            "role": "gateway",
            "status": "active",
            "description": "Primary LLM routing, caching, and provider management",
        },
        {
            "name": "9Router Backup",
            "role": "backup",
            "status": "active",
            "description": "Backup LLM router with failover intelligence",
        },
        {
            "name": "OpenHands Engineer",
            "role": "engineer",
            "status": "active",
            "description": "Autonomous coding agent for software engineering tasks",
        },
        {
            "name": "Cloudflare Edge Agent",
            "role": "edge",
            "status": "active",
            "description": "Edge inference and caching at Cloudflare network",
        },
        {
            "name": "HF Spaces Agent",
            "role": "inference",
            "status": "active",
            "description": "HuggingFace model inference and ZeroGPU management",
        },
    ]

    for name, mod in _plugins.items():
        if hasattr(mod, "get_agent_info"):
            try:
                extra = mod.get_agent_info()
                if isinstance(extra, list):
                    agents.extend(extra)
                else:
                    agents.append(extra)
            except Exception:
                pass

    return {"agents": agents, "total": len(agents)}


@app.get("/api/status")
async def status():
    infra = await _get_ai_infra()
    infra_status = "not_ready"
    stats = {}
    if infra:
        try:
            detail = await infra.health_check()
            infra_status = detail.get("status", "unknown")
            stats = getattr(infra, "stats", {})
        except Exception:
            infra_status = "error"

    return {
        "service": "mavado",
        "version": "2.0.0",
        "status": "running",
        "ai_infrastructure": infra_status,
        "statistics": stats,
        "plugins": list(_plugins.keys()),
        "config": {
            "model": CONFIG.get("model", "auto"),
            "temperature": CONFIG.get("temperature", 0.7),
            "channel_type": CONFIG.get("channel_type", "wx"),
        },
    }


@app.get("/")
async def root():
    return {
        "service": "mavado",
        "version": "2.0.0",
        "description": "CEO/Orchestrator for the Autonomous AI Company",
        "endpoints": {
            "health": "/health",
            "chat": "/api/chat (POST)",
            "task": "/api/task (POST)",
            "deploy": "/api/deploy (POST)",
            "agents": "/api/agents (GET)",
            "status": "/api/status (GET)",
        },
    }


def _handle_signal(sig, _frame):
    logger.info("Received signal %s, shutting down...", sig)
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    port = int(os.environ.get("PORT", "8080"))
    host = os.environ.get("HOSTNAME", "0.0.0.0")

    logger.info("Starting MavadoClaw on %s:%s", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")
