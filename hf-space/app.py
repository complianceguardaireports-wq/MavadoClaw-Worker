"""
MavadoClaw HF Space - Gradio Interface
"""
import json
import os
import sys
import asyncio
from typing import List, Dict, Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

try:
    import gradio as gr
    HAS_GRADIO = True
except ImportError:
    HAS_GRADIO = False

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

MAVADOCLAW_API_URL = os.environ.get("MAVADOCLAW_API_URL", "http://localhost:8080")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")


async def chat_fn(message, history, model, temperature):
    if not MAVADOCLAW_API_URL:
        return "MAVADOCLAW_API_URL not configured."

    messages = []
    for h in history:
        if isinstance(h, dict):
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": message})

    payload = {
        "messages": messages,
        "model": model,
        "temperature": temperature,
        "stream": False,
    }

    headers = {"Content-Type": "application/json"}
    if ADMIN_TOKEN:
        headers["Authorization"] = f"Bearer {ADMIN_TOKEN}"

    try:
        if HAS_AIOHTTP:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{MAVADOCLAW_API_URL}/api/chat",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if isinstance(result, dict) and "choices" in result:
                            return result["choices"][0]["message"]["content"]
                        return str(result)
                    else:
                        text = await resp.text()
                        return f"Error {resp.status}: {text}"
        else:
            import urllib.request
            req = urllib.request.Request(
                f"{MAVADOCLAW_API_URL}/api/chat",
                data=json.dumps(payload).encode(),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode())
                if isinstance(result, dict) and "choices" in result:
                    return result["choices"][0]["message"]["content"]
                return str(result)
    except Exception as e:
        return f"Connection error: {str(e)}\n\nEnsure backend is running at {MAVADOCLAW_API_URL}"


def build_ui():
    if not HAS_GRADIO:
        print("Gradio not installed. Run: pip install gradio")
        return None

    with gr.Blocks(
        title="MavadoClaw - AI Virtual Company",
        theme=gr.themes.Soft(),
    ) as demo:
        gr.Markdown(
            """
            # MavadoClaw - AI Virtual Company
            ### CEO/Orchestrator powered by OmniRoute + 9Router + Cloudflare Edge
            """
        )

        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(label="Chat", height=500)
                msg = gr.Textbox(label="Message", placeholder="Ask MavadoClaw anything...")
                with gr.Row():
                    submit = gr.Button("Send", variant="primary")
                    clear = gr.Button("Clear")

            with gr.Column(scale=1):
                model = gr.Dropdown(
                    choices=["auto", "fast", "balanced", "powerful", "coding", "reasoning"],
                    value="auto",
                    label="Model",
                )
                temperature = gr.Slider(
                    minimum=0.0, maximum=2.0, value=0.7, step=0.1, label="Temperature"
                )
                gr.Markdown(
                    """
                    **Commands:**
                    - `dev: <task>` - Coding task
                    - `route: <model> <prompt>` - Direct LLM
                    - `status` - Health check
                    - `deploy <project>` - Deploy

                    **Free APIs Active:**
                    - OmniRoute (primary)
                    - 9Router (backup)
                    - Cloudflare Edge
                    """
                )

        async def respond(message, history):
            response = await chat_fn(message, history, model.value, temperature.value)
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": response})
            return "", history

        msg.submit(respond, [msg, chatbot], [msg, chatbot])
        submit.click(respond, [msg, chatbot], [msg, chatbot])
        clear.click(lambda: ([], ""), outputs=[chatbot, msg])

    return demo


# ==================== FastAPI App ====================
app = FastAPI(title="MavadoClaw Frontend")


@app.middleware("http")
async def health_check(request: Request, call_next):
    if request.url.path == "/health":
        return JSONResponse({"status": "healthy"})
    return await call_next(request)


@app.get("/api/info")
async def info():
    return JSONResponse({
        "app": "MavadoClaw Frontend",
        "gradio": HAS_GRADIO,
        "backend": MAVADOCLAW_API_URL,
    })


# Mount Gradio at root if available
demo = build_ui()
if demo:
    try:
        app = gr.mount_gradio_app(app, demo, path="/")
    except (ImportError, AttributeError):
        pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
