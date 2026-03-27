"""Agente especializado en QA y validación."""
import logging
from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager

from lib.config import cfg
from lib.hooks import MaxToolCallsHook
from lib.agents.tools_registry import QA_TOOLS
from lib.agents.sub_agents.qa.prompt import QA_PROMPT

logger = logging.getLogger("agent.qa")


def build_qa_agent(model) -> Agent:
    """Crea el agente especializado en QA y validación del proyecto.

    Args:
        model: Instancia del modelo LLM compartido.

    Returns:
        Agent configurado para QA y validación.
    """
    agent = Agent(
        model=model,
        system_prompt=QA_PROMPT,
        tools=QA_TOOLS,
        hooks=[MaxToolCallsHook(max_calls=cfg.agent.max_tool_calls)],
        conversation_manager=SlidingWindowConversationManager(window_size=500),
    )
    logger.info("qa | agente creado tools=%d", len(QA_TOOLS))
    return agent
