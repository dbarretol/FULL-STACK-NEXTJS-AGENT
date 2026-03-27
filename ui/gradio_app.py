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
    # Persiste el sandbox_id para que dev_server.py pueda conectarse
    with open(".sandbox_id", "w") as f:
        f.write(sbx.sandbox_id)
    print(f"✅ Sandbox activo: {sbx.sandbox_id} (guardado en .sandbox_id)")
    system = build_multi_agent_system(sbx)

    def add_user_message(user_message: str, history: list):
        if not user_message.strip():
            return "", history
        history.append({"role": "user", "content": user_message})
        return "", history

    def bot_response(history: list) -> list:
        user_message = history[-1]["content"]
        reply = system.run(user_message)
        history.append({"role": "assistant", "content": reply})
        return history

    def reset() -> tuple[list, str]:
        system.reset()
        return [], ""

    with gr.Blocks(title="Agente Full Stack 🤖", fill_height=True) as demo:
        gr.Markdown("# 🤖 Agente Full Stack Multi-Agente — Next.js + E2B")

        chatbot = gr.Chatbot(
            label="Conversación",
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

        btn.click(
            add_user_message, inputs=[txt, chatbot], outputs=[txt, chatbot]
        ).then(
            bot_response, inputs=[chatbot], outputs=[chatbot]
        )

        txt.submit(
            add_user_message, inputs=[txt, chatbot], outputs=[txt, chatbot]
        ).then(
            bot_response, inputs=[chatbot], outputs=[chatbot]
        )

    return demo


if __name__ == "__main__":
    create_ui().launch(
        share=cfg.gradio.share,
        height=cfg.gradio.height,
        theme=gr.themes.Soft(),
        css="""
        .gradio-container { height: 100vh !important; }
        #chatbot { flex-grow: 1 !important; overflow-y: auto !important; }
        """,
    )
