"""
Fábrica de agentes especializados.
Cada función retorna un Agent de Strands configurado para su rol.
Los agentes se crean bajo demanda para evitar overhead innecesario.
"""
import logging
from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager

from lib.config import cfg
from lib.hooks import MaxToolCallsHook
from lib.agents.prompts import (
    FRONTEND_PROMPT,
    BACKEND_PROMPT,
    UIUX_PROMPT,
    QA_PROMPT,
    CONTEXT_AGENT_PROMPT,
)
from lib.agents.tools_registry import (
    FRONTEND_TOOLS,
    BACKEND_TOOLS,
    UIUX_TOOLS,
    QA_TOOLS,
    CONTEXT_TOOLS,
)

logger = logging.getLogger("agent.specialized")


def _make_agent(name: str, system_prompt: str, tools: list, model, max_tool_calls: int | None = None) -> Agent:
    """Crea un agente Strands con configuración estándar.

    Args:
        name: Nombre del agente (para logging).
        system_prompt: Prompt de sistema especializado.
        tools: Lista de herramientas disponibles para este agente.
        model: Instancia del modelo LLM.
        max_tool_calls: Límite de llamadas a herramientas. None usa el valor de cfg.

    Returns:
        Instancia de Agent lista para usar.
    """
    calls_limit = max_tool_calls if max_tool_calls is not None else cfg.agent.max_tool_calls
    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        tools=tools,
        hooks=[MaxToolCallsHook(max_calls=calls_limit)],
        conversation_manager=SlidingWindowConversationManager(window_size=500),
    )
    logger.info("specialized | agente '%s' creado tools=%d max_calls=%d", name, len(tools), calls_limit)
    return agent


def build_frontend_agent(model) -> Agent:
    """Crea el agente especializado en desarrollo Frontend Next.js.

    Args:
        model: Instancia del modelo LLM compartido.

    Returns:
        Agent configurado para desarrollo frontend.
    """
    return _make_agent("frontend", FRONTEND_PROMPT, FRONTEND_TOOLS, model)


def build_backend_agent(model) -> Agent:
    """Crea el agente especializado en Backend/API Routes de Next.js.

    Args:
        model: Instancia del modelo LLM compartido.

    Returns:
        Agent configurado para desarrollo backend.
    """
    return _make_agent("backend", BACKEND_PROMPT, BACKEND_TOOLS, model)


def build_uiux_agent(model) -> Agent:
    """Crea el agente especializado en diseño UI/UX.

    Args:
        model: Instancia del modelo LLM compartido.

    Returns:
        Agent configurado para diseño UI/UX.
    """
    return _make_agent("uiux", UIUX_PROMPT, UIUX_TOOLS, model)


def build_qa_agent(model) -> Agent:
    """Crea el agente especializado en QA y validación del proyecto.

    Args:
        model: Instancia del modelo LLM compartido.

    Returns:
        Agent configurado para QA y validación.
    """
    return _make_agent("qa", QA_PROMPT, QA_TOOLS, model)


def build_context_agent(model) -> Agent:
    """Crea el agente especializado en compresión y gestión de contexto.

    Args:
        model: Instancia del modelo LLM compartido.

    Returns:
        Agent configurado para gestión de contexto.
    """
    return _make_agent("context", CONTEXT_AGENT_PROMPT, CONTEXT_TOOLS, model, max_tool_calls=5)
