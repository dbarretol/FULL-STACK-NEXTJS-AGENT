"""Agente especializado en compresión y gestión de contexto."""
import logging
from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager

from lib.hooks import MaxToolCallsHook
from lib.agents.tools_registry import CONTEXT_TOOLS
from lib.agents.sub_agents.context.prompt import CONTEXT_AGENT_PROMPT

logger = logging.getLogger("agent.context")


def build_context_agent(model) -> Agent:
    """Crea el agente especializado en compresión y gestión de contexto.

    Args:
        model: Instancia del modelo LLM compartido.

    Returns:
        Agent configurado para gestión de contexto.
    """
    agent = Agent(
        model=model,
        system_prompt=CONTEXT_AGENT_PROMPT,
        tools=CONTEXT_TOOLS,
        hooks=[MaxToolCallsHook(max_calls=5)],
        conversation_manager=SlidingWindowConversationManager(window_size=500),
    )
    logger.info("context | agente creado tools=%d", len(CONTEXT_TOOLS))
    return agent
