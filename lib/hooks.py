"""
Hooks de Strands para controlar el comportamiento del agente.
"""
from threading import Lock

from strands.hooks import HookProvider, HookRegistry, BeforeToolCallEvent, BeforeInvocationEvent


class MaxToolCallsHook(HookProvider):
    """Limita el número total de llamadas a herramientas por invocación del agente.

    Cuando se alcanza el límite, cancela cualquier llamada adicional con un
    mensaje de error para que el agente finalice su respuesta.

    Args:
        max_calls: Número máximo de llamadas a herramientas permitidas por tarea.
    """

    def __init__(self, max_calls: int = 50) -> None:
        self.max_calls = max_calls
        self._count = 0
        self._lock = Lock()

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, self._reset)
        registry.add_callback(BeforeToolCallEvent, self._check_limit)

    def _reset(self, event: BeforeInvocationEvent) -> None:
        """Reinicia el contador al inicio de cada invocación."""
        with self._lock:
            self._count = 0

    def _check_limit(self, event: BeforeToolCallEvent) -> None:
        """Cancela la herramienta si se superó el límite."""
        with self._lock:
            self._count += 1
            count = self._count

        if count > self.max_calls:
            event.cancel_tool = (
                f"Límite de {self.max_calls} llamadas a herramientas alcanzado. "
                "Detén el trabajo y entrega el resultado parcial que tienes hasta ahora."
            )
