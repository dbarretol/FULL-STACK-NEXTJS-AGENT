import sys
import os

# Añadir el directorio actual al path para importar lib
sys.path.append(os.getcwd())

from lib.smart_logging import SmartLoggingHook
from strands.hooks import MessageAddedEvent, BeforeToolCallEvent, AfterToolCallEvent
import logging

# Mock de ToolResult ya que no podemos instanciarlo fácilmente sin dependencias complejas
class MockToolResult:
    def __init__(self, content):
        self.content = content

def test_logging():
    hook = SmartLoggingHook("frontend_agent")
    
    # 1. Simular pensamiento (Narrativa)
    print("TEST 1: Pensamiento del agente")
    event_thought = MessageAddedEvent(
        agent=None,
        message={"role": "assistant", "content": [{"text": "Analizando la estructura del proyecto en busca de archivos page.tsx."}]}
    )
    hook.on_message_added(event_thought)
    
    # 2. Simular Tool Call (Acción)
    print("\nTEST 2: Llamada a herramienta (write_file)")
    event_before = BeforeToolCallEvent(
        agent=None,
        selected_tool=None,
        tool_use={"name": "write_file", "input": {"path": "app/page.tsx", "content": "export default function Page() { ... }"}},
        invocation_state={}
    )
    hook.on_before_tool_call(event_before)
    
    # 3. Simular Tool Result (Resultado exitoso)
    print("\nTEST 3: Resultado de herramienta")
    event_after = AfterToolCallEvent(
        agent=None,
        selected_tool=None,
        tool_use={"name": "write_file", "input": {"path": "app/page.tsx"}},
        invocation_state={},
        result=MockToolResult([{"text": "Successfully wrote file to app/page.tsx"}])
    )
    hook.on_after_tool_call(event_after)

    # 4. Simular Error (Excepción)
    print("\nTEST 4: Excepción en herramienta (run_command)")
    event_error = AfterToolCallEvent(
        agent=None,
        selected_tool=None,
        tool_use={"name": "run_command", "input": {"command": "npx tsc --noEmit"}},
        invocation_state={},
        result=None,
        exception=Exception("Command exited with code 1. Details: src/app/page.tsx:10:5 - error TS2322")
    )
    hook.on_after_tool_call(event_error)

    # 5. Simular Pensamiento + Tool Use en el mismo mensaje (No debería mostrar el pensamiento por duplicado si el sistema lo maneja separadamente)
    print("\nTEST 5: Mensaje mixto (Pensamiento + Tool Use)")
    event_mixed = MessageAddedEvent(
        agent=None,
        message={"role": "assistant", "content": [
            {"text": "Voy a crear el archivo ahora."},
            {"toolUse": {"name": "write_file", "input": {}}}
        ]}
    )
    hook.on_message_added(event_mixed) # No debería imprimir nada porque tiene toolUse

if __name__ == "__main__":
    test_logging()
