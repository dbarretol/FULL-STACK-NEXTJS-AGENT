"""
Punto de entrada del agente Full Stack multi-agente.
Crea el sandbox E2B y lanza el sistema multi-agente coordinado por el orquestador.
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

from e2b_code_interpreter import Sandbox
from lib.config import cfg
from lib.agents.orchestrator import MultiAgentSystem, build_multi_agent_system


def main() -> None:
    """Punto de entrada CLI: crea sandbox y ejecuta las tareas de prueba del FinalGoal."""
    print("🚀 Iniciando sandbox E2B...")
    sbx = Sandbox.create(timeout=cfg.sandbox.timeout_seconds)
    print(f"✅ Sandbox activo: {sbx.sandbox_id}")
    with open(".sandbox_id", "w") as f:
        f.write(sbx.sandbox_id)
    print("📝 Sandbox ID guardado en .sandbox_id")

    system = build_multi_agent_system(sbx)

    print("\n" + "=" * 60)
    print("TAREA 1: Crear app de lista de tareas estilo Windows 95")
    print("=" * 60)
    print(f"\n[Agente]: {system.run('Crea una app de lista de tareas estilo Windows 95.')}")

    print("\n" + "=" * 60)
    print("TAREA 2: Corregir íconos del nav")
    print("=" * 60)
    print(f"\n[Agente]: {system.run('Los íconos del nav son blancos y no se ven. Arréglalo.')}")

    sbx.kill()
    print("\n✅ Sandbox cerrado.")


if __name__ == "__main__":
    main()
