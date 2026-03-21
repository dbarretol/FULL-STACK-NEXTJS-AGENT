"""
Interfaz Gradio para el agente Full Stack.
Ejecutar con: python -m ui.gradio_app
La configuración de la UI se lee desde lib/config/settings.yaml (gradio section).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import gradio as gr
from e2b_code_interpreter import Sandbox

from lib.config import cfg
from main import build_agent, run_task


def create_ui() -> gr.Blocks:
    """Crea la interfaz Gradio con historial de conversación persistente."""
    sbx = Sandbox(timeout=cfg.sandbox.timeout_seconds)
    agent, model = build_agent(sbx)

    def chat(user_message: str, history: list) -> tuple[str, list]:
        if not user_message.strip():
            return "", history
        reply = run_task(agent, model, user_message)
        history.append((user_message, reply))
        return "", history

    def reset() -> tuple[list, str]:
        agent.messages = []
        return [], ""

    with gr.Blocks(theme=gr.themes.Soft(), title="Agente Full Stack 🤖") as demo:
        gr.Markdown("# 🤖 Agente Full Stack — Next.js + AWS Bedrock + E2B")

        chatbot = gr.Chatbot(label="Conversación", height=500, bubble_full_width=False)

        with gr.Row():
            txt = gr.Textbox(
                placeholder="Ej: Crea una app de lista de tareas estilo Windows 95",
                label="Instrucción",
                scale=9,
            )
            btn = gr.Button("Enviar ➤", variant="primary", scale=1)

        reset_btn = gr.Button("🗑️ Nueva conversación", variant="secondary")
        reset_btn.click(reset, outputs=[chatbot, txt])

        gr.Examples(
            examples=[
                ["Crea una app de lista de tareas estilo Windows 95."],
                ["Los íconos del nav son blancos y no se ven. Arréglalo."],
                ["Agrega un modo oscuro a la aplicación."],
                ["Crea una landing page para una startup de IA."],
            ],
            inputs=txt,
        )

        btn.click(chat, inputs=[txt, chatbot], outputs=[txt, chatbot])
        txt.submit(chat, inputs=[txt, chatbot], outputs=[txt, chatbot])

    return demo


if __name__ == "__main__":
    create_ui().launch(share=cfg.gradio.share, height=cfg.gradio.height)
