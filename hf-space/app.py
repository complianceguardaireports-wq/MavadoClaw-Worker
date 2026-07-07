"""
MavadoClaw HF Space - Gradio Interface
Deploy this as a HuggingFace Docker Space for web-based access
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import gradio as gr
    HAS_GRADIO = True
except ImportError:
    HAS_GRADIO = False

from app import app, ChatRequest, ChatMessage, load_config


CONFIG = load_config()


async def chat_fn(message, history, model, temperature):
    messages = []
    for h in history:
        messages.append(ChatMessage(role=h["role"], content=h["content"]))
    messages.append(ChatMessage(role="user", content=message))

    try:
        from app import _get_ai_infra
        infra = await _get_ai_infra()
        if infra:
            result = await infra.chat_completion(
                [m.model_dump() for m in messages],
                model=model,
                temperature=temperature,
            )
            if isinstance(result, dict) and "choices" in result:
                return result["choices"][0]["message"]["content"]
            return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

    return "AI infrastructure not available. Please ensure OmniRoute and 9Router are running."


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

        def respond(message, history):
            response = chat_fn(message, history, model.value, temperature.value)
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": response})
            return "", history

        msg.submit(respond, [msg, chatbot], [msg, chatbot])
        submit.click(respond, [msg, chatbot], [msg, chatbot])
        clear.click(lambda: ([], ""), outputs=[chatbot, msg])

    return demo


if __name__ == "__main__":
    demo = build_ui()
    if demo:
        demo.launch(server_name="0.0.0.0", server_port=7860)
    else:
        print("Starting without Gradio UI. Use API directly.")
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=7860)
