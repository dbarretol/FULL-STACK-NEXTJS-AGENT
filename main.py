"""
Punto de entrada del agente Full Stack.
Crea el sandbox E2B, construye el modelo desde lib.llm y lanza el agente Strands.
Toda la configuración se lee desde lib/config/settings.yaml.
"""
import logging
import sys
from dotenv import load_dotenv

# Cargar variables de entorno (E2B_API_KEY, AWS, etc.) antes de inicializar nada
load_dotenv()

# Configuración de logging: INFO a consola, DEBUG a archivo
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)-8s] %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("agent.log", encoding="utf-8"),
    ],
)
# Silencia librerías ruidosas
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("gradio").setLevel(logging.WARNING)

logger = logging.getLogger("agent.main")

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
    run_command,
    start_dev_server,
    validate_app,
)
from lib.context_manager import maybe_compress
from lib.hooks import MaxToolCallsHook
from lib.prompts import SYSTEM_PROMPT_WEB_DEV

_TOOLS = [execute_code, list_directory, read_file, write_file,
          search_file_content, replace_in_file, glob_files,
          run_command, start_dev_server, validate_app]


def build_agent(sbx: Sandbox) -> tuple[Agent, object]:
    """Construye el agente Strands con el sandbox E2B inyectado.

    El modelo se construye según lib/config/settings.yaml (llm_provider).

    Args:
        sbx: Sandbox E2B activo.

    Returns:
        Tupla (agent, model) listos para usar.
    """
    logger.info("build_agent | sandbox_id=%s provider=%s model=%s",
                sbx.sandbox_id, cfg.llm_provider, cfg.model.model_id)
    tools_module.sbx = sbx

    model = build_model()
    logger.info("build_agent | model built OK")

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT_WEB_DEV,
        tools=_TOOLS,
        hooks=[MaxToolCallsHook(max_calls=cfg.agent.max_tool_calls)],
    )
    logger.info("build_agent | agent ready tools=%d max_tool_calls=%d",
                len(_TOOLS), cfg.agent.max_tool_calls)
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
    logger.info("run_task START | query=%s", query[:100])
    maybe_compress(agent, model)
    result = str(agent(query))
    logger.info("run_task END | response_len=%d", len(result))
    return result


def main() -> None:
    """Punto de entrada CLI: crea sandbox y ejecuta las tareas de prueba del FinalGoal."""
    print("🚀 Iniciando sandbox E2B...")
    sbx = Sandbox.create(timeout=cfg.sandbox.timeout_seconds)
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
