"""Agente especializado en Backend/API Routes de Next.js."""
import logging
from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager

from lib.config import cfg
from lib.hooks import MaxToolCallsHook
from lib.agents.tools_registry import BACKEND_TOOLS
from lib.agents.sub_agents.backend.prompt import BACKEND_PROMPT

logger = logging.getLogger("agent.backend")


def build_backend_agent(model) -> Agent:
    """Crea el agente especializado en Backend/API Routes de Next.js.

    Args:
        model: Instancia del modelo LLM compartido.

    Returns:
        Agent configurado para desarrollo backend.
    """
    agent = Agent(
        model=model,
        system_prompt=BACKEND_PROMPT,
        tools=BACKEND_TOOLS,
        hooks=[MaxToolCallsHook(max_calls=cfg.agent.max_tool_calls)],
        conversation_manager=SlidingWindowConversationManager(window_size=500),
    )
    logger.info("backend | agente creado tools=%d", len(BACKEND_TOOLS))
    return agent
