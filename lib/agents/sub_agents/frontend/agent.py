"""Agente especializado en desarrollo Frontend Next.js."""
import logging
from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager

from lib.config import cfg
from lib.hooks import MaxToolCallsHook
from lib.agents.tools_registry import FRONTEND_TOOLS
from lib.agents.sub_agents.frontend.prompt import FRONTEND_PROMPT

logger = logging.getLogger("agent.frontend")


def build_frontend_agent(model) -> Agent:
    """Crea el agente especializado en desarrollo Frontend Next.js.

    Args:
        model: Instancia del modelo LLM compartido.

    Returns:
        Agent configurado para desarrollo frontend.
    """
    agent = Agent(
        model=model,
        system_prompt=FRONTEND_PROMPT,
        tools=FRONTEND_TOOLS,
        hooks=[MaxToolCallsHook(max_calls=cfg.agent.max_tool_calls)],
        conversation_manager=SlidingWindowConversationManager(window_size=500),
    )
    logger.info("frontend | agente creado tools=%d", len(FRONTEND_TOOLS))
    return agent
