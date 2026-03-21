"""
Punto de entrada del agente Full Stack.
Crea el sandbox E2B, configura el modelo Bedrock y lanza el agente Strands.
"""
import os
import lib.tools as tools_module
from e2b_code_interpreter import Sandbox
from strands import Agent
from strands.models.bedrock import BedrockModel

from lib.tools import (
    execute_code,
    list_directory,
    read_file,
    write_file,
    search_file_content,
    replace_in_file,
    glob_files,
)
from lib.context_manager import maybe_compress
from lib.prompts import SYSTEM_PROMPT_WEB_DEV


def build_agent(sbx: Sandbox) -> tuple[Agent, BedrockModel]:
    """Construye el agente Strands con el sandbox E2B inyectado.

    Args:
        sbx: Sandbox E2B activo.

    Returns:
        Tupla (agent, model) listos para usar.
    """
    # Inyectar sandbox como global de módulo (las @tool lo leen desde ahí)
    tools_module.sbx = sbx

    model = BedrockModel(
        model_id="amazon.nova-pro-v1:0",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        temperature=0.2,
        max_tokens=4096,
    )

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT_WEB_DEV,
        tools=[execute_code, list_directory, read_file, write_file,
               search_file_content, replace_in_file, glob_files],
        max_handler_calls=30,  # Equivalente a max_steps; suficiente para tareas de web dev
    )

    return agent, model


def run_task(agent: Agent, model: BedrockModel, query: str) -> str:
    """Ejecuta una tarea en el agente con compresión de contexto automática.

    Args:
        agent: Instancia del agente Strands.
        model: Modelo Bedrock (usado para compresión si es necesario).
        query: Instrucción en lenguaje natural.

    Returns:
        Respuesta final del agente como string.
    """
    maybe_compress(agent, model)
    response = agent(query)
    return str(response)


def main() -> None:
    """Punto de entrada CLI: crea sandbox y ejecuta las tareas de prueba del FinalGoal."""
    print("🚀 Iniciando sandbox E2B...")
    sbx = Sandbox(timeout=60 * 60)
    print(f"✅ Sandbox activo: {sbx.sandbox_id}")

    agent, model = build_agent(sbx)

    # --- Tarea 1 ---
    print("\n" + "=" * 60)
    print("TAREA 1: Crear app de lista de tareas estilo Windows 95")
    print("=" * 60)
    respuesta1 = run_task(agent, model, "Crea una app de lista de tareas estilo Windows 95.")
    print(f"\n[Agente]: {respuesta1}")

    # --- Tarea 2 (mismo historial) ---
    print("\n" + "=" * 60)
    print("TAREA 2: Corregir íconos del nav")
    print("=" * 60)
    respuesta2 = run_task(agent, model, "Los íconos del nav son blancos y no se ven. Arréglalo.")
    print(f"\n[Agente]: {respuesta2}")

    sbx.kill()
    print("\n✅ Sandbox cerrado.")


if __name__ == "__main__":
    main()
