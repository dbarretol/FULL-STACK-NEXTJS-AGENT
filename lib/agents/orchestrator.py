"""
Agente Orquestador del sistema multi-agente.
Usa el patrón 'Agent as Tool' de Strands para delegar tareas a agentes especializados.
El orquestador no implementa código directamente — solo coordina.
"""
import logging
from strands import Agent
from strands.tools import tool
from strands.agent.conversation_manager import SlidingWindowConversationManager

from lib.config import cfg
from lib.hooks import MaxToolCallsHook
from lib.llm import build_model
from lib.context_manager import maybe_compress
from lib.agents.prompts import ORCHESTRATOR_PROMPT
from lib.agents.sub_agents.frontend.agent import build_frontend_agent
from lib.agents.sub_agents.backend.agent import build_backend_agent
from lib.agents.sub_agents.uiux.agent import build_uiux_agent
from lib.agents.sub_agents.qa.agent import build_qa_agent
from lib.agents.sub_agents.context.agent import build_context_agent
import lib.tools as tools_module
from e2b_code_interpreter import Sandbox

logger = logging.getLogger("agent.orchestrator")


class MultiAgentSystem:
    """Sistema multi-agente coordinado por un orquestador central.

    Mantiene instancias de todos los agentes especializados y expone
    el orquestador como punto de entrada único.

    Args:
        sbx: Sandbox E2B activo.
    """

    def __init__(self, sbx: Sandbox) -> None:
        logger.info("MultiAgentSystem | inicializando sandbox_id=%s", sbx.sandbox_id)

        # Inyectar sandbox en el módulo de herramientas (global compartido)
        tools_module.sbx = sbx
        self._sbx = sbx

        # Modelo compartido entre todos los agentes
        self._model = build_model()
        logger.info("MultiAgentSystem | modelo construido provider=%s model=%s",
                    cfg.llm_provider, cfg.model.model_id)

        # Construir agentes especializados
        self._frontend = build_frontend_agent(self._model)
        self._backend = build_backend_agent(self._model)
        self._uiux = build_uiux_agent(self._model)
        self._qa = build_qa_agent(self._model)
        self._context = build_context_agent(self._model)

        # Construir herramientas de delegación
        agent_tools = self._build_agent_tools()

        # Orquestador principal — límite más alto porque coordina múltiples agentes
        self._orchestrator = Agent(
            model=self._model,
            system_prompt=ORCHESTRATOR_PROMPT,
            tools=agent_tools,
            hooks=[MaxToolCallsHook(max_calls=cfg.agent.max_tool_calls * 3)],
            conversation_manager=SlidingWindowConversationManager(window_size=200),
        )
        logger.info("MultiAgentSystem | orquestador listo con %d herramientas de delegación",
                    len(agent_tools))

    def _build_agent_tools(self) -> list:
        """Crea las herramientas de delegación usando @tool(name=, description=) de Strands.

        Cada agente especializado se envuelve en una función @tool con nombre y
        descripción explícitos. Se usan variables locales para capturar las referencias
        a los agentes en los closures de forma segura.

        Returns:
            Lista de funciones @tool que delegan al agente correspondiente.
        """
        _frontend = self._frontend
        _backend = self._backend
        _uiux = self._uiux
        _qa = self._qa
        _context = self._context
        _model = self._model

        @tool(
            name="frontend_agent",
            description=(
                "Delegate a frontend development task to the Next.js specialist agent. "
                "Use for: creating pages, React components, hooks, client/server logic, "
                "implementing new features in the UI, fixing TypeScript errors in components."
            ),
        )
        def frontend_agent(task: str) -> str:
            """Delegate a frontend task to the Next.js specialist.

            Args:
                task: Detailed description of the frontend task to implement.

            Returns:
                Agent response describing what was implemented.
            """
            logger.info("frontend_agent DELEGATING | task=%.100s", task)
            maybe_compress(_frontend, _model)
            result = str(_frontend(task))
            logger.info("frontend_agent DONE | response_len=%d", len(result))
            return result

        @tool(
            name="backend_agent",
            description=(
                "Delegate a backend/API development task to the Next.js API specialist agent. "
                "Use for: creating API routes, server actions, middleware, data fetching logic, "
                "external service integrations, authentication handlers."
            ),
        )
        def backend_agent(task: str) -> str:
            """Delegate a backend task to the API specialist.

            Args:
                task: Detailed description of the backend task to implement.

            Returns:
                Agent response describing what was implemented.
            """
            logger.info("backend_agent DELEGATING | task=%.100s", task)
            maybe_compress(_backend, _model)
            result = str(_backend(task))
            logger.info("backend_agent DONE | response_len=%d", len(result))
            return result

        @tool(
            name="uiux_agent",
            description=(
                "Delegate a UI/UX design task to the design specialist agent. "
                "Use for: improving visual design, fixing contrast issues, applying color palettes, "
                "improving typography, spacing, layout, adding animations, ensuring accessibility."
            ),
        )
        def uiux_agent(task: str) -> str:
            """Delegate a UI/UX task to the design specialist.

            Args:
                task: Detailed description of the UI/UX improvement to apply.

            Returns:
                Agent response describing what was changed.
            """
            logger.info("uiux_agent DELEGATING | task=%.100s", task)
            maybe_compress(_uiux, _model)
            result = str(_uiux(task))
            logger.info("uiux_agent DONE | response_len=%d", len(result))
            return result

        @tool(
            name="qa_agent",
            description=(
                "Delegate validation and QA tasks to the quality assurance specialist agent. "
                "Use for: validating the app compiles, running TypeScript checks, starting the "
                "dev server, verifying the preview URL is accessible, detecting build errors. "
                "Always call this before reporting the final URL to the user."
            ),
        )
        def qa_agent(task: str) -> str:
            """Delegate a QA/validation task to the QA specialist.

            Args:
                task: Description of what to validate (e.g. 'validate and start server').

            Returns:
                Agent response with validation results and preview URL if successful.
            """
            logger.info("qa_agent DELEGATING | task=%.100s", task)
            maybe_compress(_qa, _model)
            result = str(_qa(task))
            logger.info("qa_agent DONE | response_len=%d", len(result))
            return result

        @tool(
            name="context_agent",
            description=(
                "Delegate context compression to the context management specialist agent. "
                "Use for: summarizing long conversation history to reduce token usage."
            ),
        )
        def context_agent(task: str) -> str:
            """Delegate a context compression task to the context specialist.

            Args:
                task: Description of what to summarize.

            Returns:
                Compressed summary of the conversation.
            """
            logger.info("context_agent DELEGATING | task=%.100s", task)
            result = str(_context(task))
            logger.info("context_agent DONE | response_len=%d", len(result))
            return result

        return [frontend_agent, backend_agent, uiux_agent, qa_agent, context_agent]

    def run(self, query: str) -> str:
        """Ejecuta una tarea a través del orquestador.

        Comprime el contexto del orquestador si supera el umbral antes de cada llamada.

        Args:
            query: Instrucción en lenguaje natural del usuario.

        Returns:
            Respuesta final del orquestador como string.
        """
        logger.info("MultiAgentSystem.run START | query=%.100s", query)
        maybe_compress(self._orchestrator, self._model)
        result = str(self._orchestrator(query))
        logger.info("MultiAgentSystem.run END | response_len=%d", len(result))
        return result

    def reset(self) -> None:
        """Limpia el historial de todos los agentes para iniciar una nueva sesión."""
        logger.info("MultiAgentSystem.reset | limpiando historial de todos los agentes")
        self._orchestrator.messages = []
        self._frontend.messages = []
        self._backend.messages = []
        self._uiux.messages = []
        self._qa.messages = []
        self._context.messages = []

    @property
    def model(self):
        """Modelo LLM compartido."""
        return self._model


def build_multi_agent_system(sbx: Sandbox) -> MultiAgentSystem:
    """Construye y retorna el sistema multi-agente completo.

    Args:
        sbx: Sandbox E2B activo.

    Returns:
        Instancia de MultiAgentSystem lista para usar.
    """
    return MultiAgentSystem(sbx)
