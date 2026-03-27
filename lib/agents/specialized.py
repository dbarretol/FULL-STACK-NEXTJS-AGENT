"""
Shim de compatibilidad — re-exporta los builders desde sus nuevas ubicaciones.
Los agentes especializados ahora viven en lib/agents/sub-agents/<agente>/agent.py
"""
from lib.agents.sub_agents.frontend.agent import build_frontend_agent
from lib.agents.sub_agents.backend.agent import build_backend_agent
from lib.agents.sub_agents.uiux.agent import build_uiux_agent
from lib.agents.sub_agents.qa.agent import build_qa_agent
from lib.agents.sub_agents.context.agent import build_context_agent

__all__ = [
    "build_frontend_agent",
    "build_backend_agent",
    "build_uiux_agent",
    "build_qa_agent",
    "build_context_agent",
]
