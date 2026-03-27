import logging
import json
import threading
from typing import Any
from strands.hooks import HookProvider, HookRegistry, MessageAddedEvent, BeforeToolCallEvent, AfterToolCallEvent

# ANSI Colors for console
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

class SmartLoggingHook(HookProvider):
    """Hook para mejorar la trazabilidad y narrativa de los agentes en consola."""
    
    _global_counter = 0
    _counter_lock = threading.Lock()

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self._logger = logging.getLogger(f"agent.trace.{agent_name}")

    @classmethod
    def _get_next_id(cls):
        with cls._counter_lock:
            cls._global_counter += 1
            return cls._global_counter

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(MessageAddedEvent, self.on_message_added)
        registry.add_callback(BeforeToolCallEvent, self.on_before_tool_call)
        registry.add_callback(AfterToolCallEvent, self.on_after_tool_call)

    def on_message_added(self, event: MessageAddedEvent):
        """Captura pensamientos y narrativa del agente cuando añade mensajes al historial."""
        message = event.message
        if message.get("role") == "assistant":
            content = message.get("content", [])
            # Extraer solo bloques de texto que no sean llamadas a herramientas (pensamiento)
            text_parts = [block.get("text", "") for block in content if "text" in block]
            full_text = "\n".join(text_parts).strip()
            
            # Si hay texto y no hay bloques de ToolUse en el mismo mensaje, es pura narrativa
            has_tool_use = any("toolUse" in block for block in content)
            
            if full_text and not has_tool_use:
                step_id = self._get_next_id()
                print(f"\n{CYAN}Tool #{step_id}: [{self.agent_name}]{RESET} {BOLD}{full_text}{RESET}")
                self._logger.debug("Narrative: %s", full_text)

    def on_before_tool_call(self, event: BeforeToolCallEvent):
        """Captura la intención de ejecución de una herramienta con sus argumentos claves."""
        step_id = self._get_next_id()
        tool_name = event.tool_use.get("name")
        args = event.tool_use.get("input", {})
        
        # Extraer info resumida para no saturar la consola
        info = ""
        if "path" in args:
            info = f" archivo={args['path']}"
        elif "command" in args:
            cmd = args['command'].replace("\n", " ")
            if len(cmd) > 60: cmd = cmd[:57] + "..."
            info = f" ejecutando='{cmd}'"
        elif "task" in args:
            task = args['task'].replace("\n", " ")
            if len(task) > 60: task = task[:57] + "..."
            info = f" tarea='{task}'"
        
        print(f"{YELLOW}Tool #{step_id}: [{self.agent_name} -> {tool_name}]{RESET}{info}")
        
        # Log detallado al archivo agent.log
        self._logger.info("ACTION | tool=%s | args=%s", tool_name, json.dumps(args, ensure_ascii=False))

    def on_after_tool_call(self, event: AfterToolCallEvent):
        """Captura el resultado de la herramienta, truncando salidas largas."""
        tool_name = event.tool_use.get("name")
        
        if event.exception:
            print(f"{RED}Tool EXCEPTION | [{self.agent_name} -> {tool_name}]{RESET} error={str(event.exception)}")
            self._logger.error("EXCEPTION | tool=%s | error=%s", tool_name, str(event.exception))
            return

        # Extraer texto del resultado (ToolResult suele tener content:[{text:...}])
        result_text = ""
        # event.result puede ser ToolResult o Exception
        if hasattr(event.result, "content"):
            content = getattr(event.result, "content") or []
            text_blocks = [b.get("text", "") for b in content if isinstance(b, dict) and "text" in b]
            result_text = "\n".join(text_blocks).strip()
        
        # Truncar para mantener la legibilidad de la consola
        if len(result_text) > 500:
            display_result = result_text[:500] + f"\n{MAGENTA}... [Salida truncada, ver agent.log para detalle completo]{RESET}"
        else:
            display_result = result_text if result_text else "[Operación completada sin salida de texto]"

        print(f"{GREEN}Resultado [{tool_name}]:{RESET} {display_result}")
        
        # Log de telemetría interna
        self._logger.debug("RESULT | tool=%s | full_len=%d", tool_name, len(result_text))
