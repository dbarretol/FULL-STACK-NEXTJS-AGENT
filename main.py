"""
Punto de entrada del agente Full Stack.
Crea el sandbox E2B, construye el modelo desde lib.llm y lanza el agente Strands.
Toda la configuración se lee desde lib/config/settings.yaml.
"""
import lib.tools as tools_module
from e2b_code_interpreter import Sandbox
from strands import Agent

from lib.config import cfg
from lib.llm import build_model
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

_TOOLS = [execute_code, list_directory, read_file, write_file,
          search_file_content, replace_in_file, glob_files]


def build_agent(sbx: Sandbox) -> tuple[Agent, object]:
    """Construye el agente Strands con el sandbox E2B inyectado.

    El modelo se construye según lib/config/settings.yaml (llm_provider).

    Args:
        sbx: Sandbox E2B activo.

    Returns:
        Tupla (agent, model) listos para usar.
    """
    tools_module.sbx = sbx  # Inyectar sandbox como global de módulo

    model = build_model()

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT_WEB_DEV,
        tools=_TOOLS,
        max_handler_calls=cfg.agent.max_handler_calls,
    )

    return agent, model


def run_task(agent: Agent, model, query: str) -> str:
    """Ejecuta una tarea en el agente con compresión de contexto automática.

    Args:
        agent: Instancia del agente Strands.
        model: Modelo activo (usado para compresión si es necesario).
        query: Instrucción en lenguaje natural.

    Returns:
        Respuesta final del agente como string.
    """
    maybe_compress(agent, model)
    return str(agent(query))


def main() -> None:
    """Punto de entrada CLI: crea sandbox y ejecuta las tareas de prueba del FinalGoal."""
    print("🚀 Iniciando sandbox E2B...")
    sbx = Sandbox(timeout=cfg.sandbox.timeout_seconds)
    print(f"✅ Sandbox activo: {sbx.sandbox_id}")

    agent, model = build_agent(sbx)

    print("\n" + "=" * 60)
    print("TAREA 1: Crear app de lista de tareas estilo Windows 95")
    print("=" * 60)
    print(f"\n[Agente]: {run_task(agent, model, 'Crea una app de lista de tareas estilo Windows 95.')}")

    print("\n" + "=" * 60)
    print("TAREA 2: Corregir íconos del nav")
    print("=" * 60)
    print(f"\n[Agente]: {run_task(agent, model, 'Los íconos del nav son blancos y no se ven. Arréglalo.')}")

    sbx.kill()
    print("\n✅ Sandbox cerrado.")


if __name__ == "__main__":
    main()
