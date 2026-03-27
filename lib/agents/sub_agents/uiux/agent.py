"""Agente especializado en diseño UI/UX."""
import logging
from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager

from lib.config import cfg
from lib.hooks import MaxToolCallsHook
from lib.agents.tools_registry import UIUX_TOOLS
from lib.agents.sub_agents.uiux.prompt import UIUX_PROMPT

logger = logging.getLogger("agent.uiux")


def build_uiux_agent(model) -> Agent:
    """Crea el agente especializado en diseño UI/UX.

    Args:
        model: Instancia del modelo LLM compartido.

    Returns:
        Agent configurado para diseño UI/UX.
    """
    agent = Agent(
        model=model,
        system_prompt=UIUX_PROMPT,
        tools=UIUX_TOOLS,
        hooks=[MaxToolCallsHook(max_calls=cfg.agent.max_tool_calls)],
        conversation_manager=SlidingWindowConversationManager(window_size=500),
    )
    logger.info("uiux | agente creado tools=%d", len(UIUX_TOOLS))
    return agent
