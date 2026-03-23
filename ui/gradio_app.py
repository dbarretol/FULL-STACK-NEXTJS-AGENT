"""
Interfaz Gradio para el sistema multi-agente Full Stack.
Ejecutar con: python -m ui.gradio_app
La configuración de la UI se lee desde lib/config/settings.yaml (gradio section).
"""
import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import gradio as gr
from e2b_code_interpreter import Sandbox

from lib.config import cfg
from lib.agents.orchestrator import MultiAgentSystem, build_multi_agent_system


def create_ui() -> gr.Blocks:
    """Crea la interfaz Gradio con historial de conversación persistente."""
    sbx = Sandbox.create(timeout=cfg.sandbox.timeout_seconds)
    system = build_multi_agent_system(sbx)

    def add_user_message(user_message: str, history: list):
        if not user_message.strip():
            return "", history
        history.append({"role": "user", "content": user_message})
        return "", history

    def bot_response(history: list) -> tuple[list, str]:
        user_message = history[-1]["content"]
        reply = system.run(user_message)
        history.append({"role": "assistant", "content": reply})

        # Extrae URL de preview de la respuesta
        preview_url = ""
        for line in reply.splitlines():
            stripped = line.strip()
            if stripped.startswith("https://") and ".e2b" in stripped:
                preview_url = stripped
                break

        return history, preview_url

    def reset() -> tuple[list, str, str]:
        system.reset()
        return [], "", ""

    custom_css = """
    .gradio-container { height: 100vh !important; }
    #chatbot { flex-grow: 1 !important; overflow-y: auto !important; }
    #chatbot > .wrapper { max-height: none !important; }
    """

    with gr.Blocks(title="Agente Full Stack 🤖", css=custom_css, fill_height=True) as demo:
        gr.Markdown("# 🤖 Agente Full Stack Multi-Agente — Next.js + E2B")

        chatbot = gr.Chatbot(
            label="Conversación",
            type="messages",
            elem_id="chatbot",
            autoscroll=True,
            scale=1,
        )

        with gr.Row():
            txt = gr.Textbox(
                placeholder="Ej: Crea una app de lista de tareas estilo Windows 95",
                label="Instrucción",
                scale=9,
            )
            btn = gr.Button("Enviar ➤", variant="primary", scale=1)

        preview_url = gr.Textbox(
            label="🌐 Preview URL (abre en el navegador)",
            interactive=False,
            visible=True,
            placeholder="La URL aparecerá aquí cuando el agente inicie el servidor...",
        )

        reset_btn = gr.Button("🗑️ Nueva conversación", variant="secondary")
        reset_btn.click(reset, outputs=[chatbot, txt, preview_url])

        gr.Examples(
            examples=[
                ["Crea una app de lista de tareas estilo Windows 95."],
                ["Los íconos del nav son blancos y no se ven. Arréglalo."],
                ["Agrega un modo oscuro a la aplicación."],
                ["Crea una landing page para una startup de IA."],
            ],
            inputs=txt,
        )

        btn.click(
            add_user_message, inputs=[txt, chatbot], outputs=[txt, chatbot]
        ).then(
            bot_response, inputs=[chatbot], outputs=[chatbot, preview_url]
        )

        txt.submit(
            add_user_message, inputs=[txt, chatbot], outputs=[txt, chatbot]
        ).then(
            bot_response, inputs=[chatbot], outputs=[chatbot, preview_url]
        )

    return demo


if __name__ == "__main__":
    create_ui().launch(share=cfg.gradio.share, height=cfg.gradio.height, theme=gr.themes.Soft())
