"""
MavadoClaw Worker - Main Entry Point
CEO/Orchestrator for the Autonomous AI Company
"""
import os
import sys
import json
import signal
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
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
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    return {}


CONFIG = load_config()


_plugins: dict = {}


def _load_plugins():
    if not PLUGIN_DIR.is_dir():
        return
    for entry in PLUGIN_DIR.iterdir():
        if entry.is_dir() and (entry / "__init__.py").exists():
            try:
                mod = __import__(f"plugins.{entry.name}", fromlist=[entry.name])
                _plugins[entry.name] = mod
            except Exception:
                pass
    for py_file in PLUGIN_DIR.glob("*.py"):
        if py_file.stem == "__init__":
            continue
        try:
            mod = __import__(f"plugins.{py_file.stem}", fromlist=[py_file.stem])
            _plugins[py_file.stem] = mod
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_plugins()
    logger.info("MavadoClaw starting on port %s", os.environ.get("PORT", "8080"))
    yield
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
    from plugins.free_inference import is_available
    return {
        "status": "healthy",
        "service": "mavado",
        "version": "2.0.0",
        "plugins": list(_plugins.keys()),
        "free_inference_available": is_available(),
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

    from plugins.free_inference import chat_completion as free_chat, is_available
    if not is_available():
        raise HTTPException(status_code=503, detail="No free inference providers available (set GROQ_API_KEY or similar)")

    result = await free_chat(messages, model=model, temperature=temperature, max_tokens=max_tokens)
    return result


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

    from plugins.free_inference import chat_completion as free_chat, is_available
    if not is_available():
        raise HTTPException(status_code=503, detail="No free inference providers available")

    result = await free_chat(messages, max_tokens=2048)
    return {"status": "completed", "agent": request.agent, "task": request.task, "result": result}


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
            "name": "Free Inference Router",
            "role": "inference",
            "status": "active",
            "description": "Multi-provider LLM failover (Groq, OpenRouter, DeepSeek, Cerebras, Mistral, GitHub Models)",
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
    from plugins.free_inference import is_available
    return {
        "service": "mavado",
        "version": "2.0.0",
        "status": "running",
        "free_inference_available": is_available(),
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
