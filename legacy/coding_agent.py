# %% [markdown]
# # 🤖 Coding Agent — AWS Bedrock + E2B + Gradio
# 
# Agente de código completo que replica el notebook original del curso, usando:
# - **AWS Bedrock** (Amazon Nova Pro) como LLM
# - **E2B** como sandbox seguro para ejecutar código
# - **Gradio** como interfaz de chat visual
# 
# 

# %% [markdown]
# ## 1. Instalación de dependencias

# %%
!pip install boto3 e2b-code-interpreter gradio -q


# %% [markdown]
# ## 2. Credenciales

# %%
import os
from google.colab import userdata

AWS_ACCESS_KEY_ID     = userdata.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = userdata.get("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION    = userdata.get("AWS_DEFAULT_REGION")
E2B_API_KEY           = userdata.get("E2B_API_KEY")

# E2B lo lee automáticamente de la variable de entorno
os.environ["E2B_API_KEY"] = E2B_API_KEY

print("Credenciales cargadas")


# %% [markdown]
# ## 3. Sandbox E2B
# 
# **E2B** (Engineer-to-Build) proporciona un sandbox de ejecución seguro y aislado.
# el código corre en un contenedor remoto,
# lo que evita que código malicioso afecte el entorno local.
# 
# `Sandbox.create()` levanta un contenedor nuevo. Lo guardamos en `sbx`
# y lo reutilizamos en todas las llamadas del agente.
# 

# %%
from e2b_code_interpreter import Sandbox

sbx = Sandbox.create(timeout=60 * 60)  # sandbox activo por 1 hora
print(f"Sandbox creado: {sbx.sandbox_id}")


# %% [markdown]
# ## 4. Cliente AWS Bedrock y función `llm`
# 
# Creamos el cliente `boto3` y una función `llm()` que:
# 1. Convierte los schemas de herramientas de formato OpenAI → Bedrock
# 2. Normaliza la respuesta de Bedrock a una interfaz común
#    (`response.output`, `response.output_text`)
# 

# %%
import boto3
import json

bedrock = boto3.client(
    service_name="bedrock-runtime",
    region_name=AWS_DEFAULT_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

MODEL_ID = "amazon.nova-pro-v1:0"


def _schema_to_bedrock(schema: dict) -> dict:
    """Convierte schema OpenAI-style a formato toolSpec de Bedrock."""
    return {
        "toolSpec": {
            "name": schema["name"],
            "description": schema.get("description", ""),
            "inputSchema": {"json": schema.get("parameters", {})},
        }
    }


def llm(client, messages, system, tools=None):
    """
    Llama a Bedrock y retorna un objeto normalizado con:
      .output       → lista de partes (type: 'message' o 'function_call')
      .output_text  → texto plano de la respuesta del asistente
    """
    kwargs = dict(
        modelId=MODEL_ID,
        system=[{"text": system}],
        messages=messages,
    )
    if tools:
        kwargs["toolConfig"] = {"tools": [_schema_to_bedrock(t) for t in tools]}

    raw = client.converse(**kwargs)
    return _BedrockResponse(raw)


class _BedrockResponse:
    def __init__(self, raw):
        self._raw        = raw
        self.output      = []
        self.output_text = ""
        self._bedrock_msg = raw["output"]["message"]
        self._parse()

    def _parse(self):
        for block in self._bedrock_msg.get("content", []):
            if "text" in block:
                self.output.append(_TextPart(block["text"]))
                self.output_text += block["text"]
            elif "toolUse" in block:
                tu = block["toolUse"]
                self.output.append(_ToolUsePart(
                    name=tu["name"],
                    arguments=json.dumps(tu["input"]),
                    call_id=tu["toolUseId"],
                ))

    def bedrock_message(self):
        return self._bedrock_msg


class _TextPart:
    type = "message"
    def __init__(self, text):
        self.text    = text
        self.content = text


class _ToolUsePart:
    type = "function_call"
    def __init__(self, name, arguments, call_id):
        self.name      = name
        self.arguments = arguments
        self.call_id   = call_id


# %% [markdown]
# Prueba rápida del LLM:

# %%
messages  = [{"role": "user", "content": [{"text": "Hola, ¿cómo estás?"}]}]
system    = "Responde siempre en español y muy brevemente."

response  = llm(bedrock, messages, system)
print(response.output_text)


# %% [markdown]
# ## 5. Herramienta `execute_code` con E2B
# 
#  `execute_code` corre el código
# en el sandbox de E2B .
# 
# `sbx.run_code(code)` devuelve un objeto `Execution` de E2B con:
# - `.text`   → output de stdout
# - `.error`  → errores si los hubo
# - `.results`→ resultados estructurados (imágenes, dataframes, etc.)
# 

# %%
def execute_code(sbx: Sandbox, code: str) -> dict:
    """Ejecuta código Python en el sandbox E2B y retorna resultado o error."""
    execution = sbx.run_code(code)

    # Capturar texto de resultados
    results = []
    for r in execution.results:
        if hasattr(r, "text") and r.text:
            results.append(r.text)

    # Capturar errores
    errors = []
    if execution.error:
        errors.append(f"{execution.error.name}: {execution.error.value}")

    # Capturar stdout / logs
    logs = []
    if execution.logs.stdout:
        logs.extend(execution.logs.stdout)
    if execution.logs.stderr:
        errors.extend(execution.logs.stderr)

    return {"results": results, "logs": logs, "errors": errors}


# %% [markdown]
# Prueba del sandbox E2B:

# %%
result = execute_code(sbx, "print('Hola desde E2B!')")
print(result)

result_error = execute_code(sbx, "1 / 0")
print(result_error)


# %% [markdown]
# ## 6. Schemas de herramientas y `execute_tool`
# 
# Los schemas siguen el formato OpenAI — la función `llm()` los convierte
# a Bedrock internamente.
# 
# **Nota sobre `execute_tool` con E2B:**
# La función `execute_code` de E2B requiere el argumento `sbx` además de `code`.
# `execute_tool` pasa `**kwargs` extras (como `sbx`) a la herramienta automáticamente.
# 

# %%
execute_code_schema = {
    "type": "function",
    "name": "execute_code",
    "description": "Ejecuta código Python en un sandbox seguro y retorna el resultado o error.",
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Código Python a ejecutar",
            }
        },
        "required": ["code"],
        "additionalProperties": False,
    },
}

read_file_schema = {
    "type": "function",
    "name": "read_file",
    "description": "Lee el contenido de un archivo en el sandbox.",
    "parameters": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Ruta del archivo"},
            "limit":     {"type": "number", "description": "Máximo de caracteres a leer"},
            "offset":    {"type": "number", "description": "Posición de inicio"},
        },
        "required": ["file_path"],
        "additionalProperties": False,
    },
}

write_file_schema = {
    "type": "function",
    "name": "write_file",
    "description": "Escribe contenido en un archivo del sandbox.",
    "parameters": {
        "type": "object",
        "properties": {
            "content":   {"type": "string", "description": "Contenido a escribir"},
            "file_path": {"type": "string", "description": "Ruta del archivo"},
        },
        "required": ["content", "file_path"],
        "additionalProperties": False,
    },
}

all_schemas = [execute_code_schema, read_file_schema, write_file_schema]


# %%
from typing import Callable, Optional, Dict, Any


def read_file(sbx: Sandbox, file_path: str,
              limit: Optional[int] = None, offset: int = 0) -> Dict[str, Any]:
    """Lee un archivo del sandbox E2B."""
    code = f"""
with open({repr(file_path)}, 'r', encoding='utf-8') as f:
    f.seek({offset})
    content = f.read({limit if limit else ''})
print(content)
"""
    result = execute_code(sbx, code)
    if result["errors"]:
        return {"error": result["errors"][0]}
    return {"content": "".join(result["logs"]), "size": len("".join(result["logs"]))}


def write_file(sbx: Sandbox, content: str, file_path: str) -> Dict[str, Any]:
    """Escribe un archivo en el sandbox E2B."""
    code = f"""
import os
os.makedirs(os.path.dirname({repr(file_path)}) or '.', exist_ok=True)
with open({repr(file_path)}, 'w', encoding='utf-8') as f:
    f.write({repr(content)})
print(f'Escrito {{len({repr(content)})}} bytes en {repr(file_path)}')
"""
    result = execute_code(sbx, code)
    if result["errors"]:
        return {"error": result["errors"][0]}
    return {"message": f"Escrito en {file_path}"}


# Mapeo nombre → función
tools = {
    "execute_code": execute_code,
    "read_file":    read_file,
    "write_file":   write_file,
}


# %%
def execute_tool(name: str, args: str, tools: dict[str, Callable], **kwargs):
    """
    Ejecuta una herramienta por nombre.
    kwargs permite pasar sbx u otros argumentos extra a la herramienta.
    """
    try:
        args_dict = json.loads(args)
        if name not in tools:
            return {"error": f"Herramienta '{name}' no existe."}
        result = tools[name](**args_dict, **kwargs)
    except json.JSONDecodeError as e:
        result = {"error": f"{name} no pudo parsear argumentos: {str(e)}"}
    except KeyError as e:
        result = {"error": f"Argumento faltante: {str(e)}"}
    except Exception as e:
        result = {"error": str(e)}
    return result


# %% [markdown]
# ## 7. Coding Agent con loop
# 
# El agente itera hasta que:
# - El LLM deja de llamar herramientas → tarea completada
# - Se llega a `max_steps` → parada de seguridad
# 
# **Formato del historial Bedrock:**
# - Mensajes del usuario: `{"role": "user", "content": [{"text": "..."}]}`
# - Resultados de tools: `{"role": "user", "content": [{"toolResult": {...}}]}`
# 

# %%
system = """Eres un programador Python senior experto. Tu tarea principal es resolver problemas escribiendo y ejecutando código.
Cuando necesites ejecutar código, *siempre* usa la herramienta `execute_code`.
Para interactuar con archivos, usa `write_file` para escribir y `read_file` para leer.
Solo responde textualmente al usuario cuando la tarea esté completada o necesites información adicional.
Responde en español.
"""

# %% [markdown]
# ## 8. Prueba básica

# %%
from typing import Callable, Optional

def coding_agent(
    client,
    query: str,
    system: str,
    tools: dict[str, Callable],
    tools_schemas: list[dict],
    sbx: Sandbox,
    messages: list[dict] = None,
    max_steps: int = 10,
) -> tuple[list, str]:
    """
    Ejecuta el agente de código con loop.
    Retorna (messages, respuesta_final) para poder encadenar conversaciones.
    """
    if messages is None:
        messages = []

    messages.append({"role": "user", "content": [{"text": query}]})
    steps       = 0
    last_output = ""

    while steps < max_steps:
        response = llm(client, messages, system, tools=tools_schemas)
        print(f"\n[paso #{steps}]")
        has_tool_call = False
        tool_results  = []

        # Agregar respuesta del asistente al historial
        messages.append(response.bedrock_message())

        for part in response.output:
            if part.type == "message":
                last_output = part.content
                print(f"[agente] {part.content}")

            elif part.type == "function_call":
                has_tool_call = True
                name = part.name
                print(f"[agente][{name}] ejecutando...")
                # Pasar sbx como kwarg extra a la herramienta
                result = execute_tool(name, part.arguments, tools, sbx=sbx)
                print(f"[{name}] → {result}")

                tool_results.append({
                    "toolResult": {
                        "toolUseId": part.call_id,
                        "content":   [{"json": result}],
                    }
                })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        if not has_tool_call:
            print("\n[agente]  tarea completada")
            break

        steps += 1
    else:
        print(f"\n[agente] límite de {max_steps} pasos alcanzado")

    return messages, last_output

messages, _ = coding_agent(
    bedrock,
    query="Escribe un programa que imprima los primeros 10 números de Fibonacci y ejecútalo.",
    system=system,
    tools=tools,
    tools_schemas=all_schemas,
    sbx=sbx,
)

# %% [markdown]
# ## 9. Prueba tu mismo:
# 
# ---
# 
# 
# 
# ---
# 
# 

# %% [markdown]
# ## Tarea: Calcular y guardar la suma de los primeros 50 números pares
# 
# **Descripción:**
# Tu objetivo es utilizar el `coding_agent` para realizar una serie de operaciones en el sandbox de E2B.
# 
# **Instrucciones:**
# 1.  **Genera** una lista con los primeros 50 números pares.
# 2.  **Calcula** la suma total de estos 50 números pares.
# 3.  **Guarda** el resultado de la suma en un archivo llamado `suma_pares.txt` .
# 4.  **Responde** al usuario con el valor de la suma una vez que la tarea esté completada.
# 
# **Recursos disponibles:**
# *   El `coding_agent` está configurado y listo para recibir instrucciones.
# *   Puedes usar las herramientas `execute_code` y `write_file`.

# %%
messages, _ = coding_agent(
    bedrock,
    query="Calcula la suma total de estos primeros 50 números pares en python. Guarda el resultado de la suma en un archivo llamado suma_pares_v2.txt. y muestra el resultado ",
    system=system,
    tools=tools,
    tools_schemas=all_schemas,
    sbx=sbx,
)

# %% [markdown]
# ## 10. Interfaz Gradio
# 
# Interfaz de chat visual igual a la del curso original (`coding_agent_demo_ui`).
# Mantiene el historial de la conversación entre mensajes.
# 

# %%
import gradio as gr

def create_chat_ui(client, system, tools, tools_schemas, sbx):
    """Crea y lanza la interfaz Gradio del agente de código."""
    conversation_messages = []

    def chat(user_message, chat_history):
        nonlocal conversation_messages

        # Llamar al agente
        conversation_messages, agent_reply = coding_agent(
            client=client,
            query=user_message,
            system=system,
            tools=tools,
            tools_schemas=tools_schemas,
            sbx=sbx,
            messages=conversation_messages,
            max_steps=10,
        )

        chat_history.append((user_message, agent_reply))
        return "", chat_history

    def reset():
        nonlocal conversation_messages
        conversation_messages = []
        return [], []

    with gr.Blocks(theme=gr.themes.Soft(), title="Coding Agent 🤖") as demo:
        gr.Markdown("""
        # 🤖 Coding Agent — AWS Bedrock + E2B
        Agente que escribe y ejecuta código Python en un sandbox seguro.
        """)

        chatbot = gr.Chatbot(
            label="Conversación",
            height=500,
            bubble_full_width=False,
        )

        with gr.Row():
            txt = gr.Textbox(
                placeholder="Ej: ¿Puedes crear una función que dibuje un emoji y ejecutarla?",
                label="Tu mensaje",
                scale=9,
            )
            btn = gr.Button("Enviar ➤", variant="primary", scale=1)

        with gr.Row():
            clear_btn = gr.Button("🗑️ Nueva conversación", variant="secondary")

        # Ejemplos de prompts
        gr.Examples(
            examples=[
                ["Crea una función que dibuje un emoji aleatorio y ejecútala"],
                ["Escribe y ejecuta un programa que calcule el factorial de 10"],
                ["Crea un archivo data.txt con los primeros 5 números primos"],
                ["Escribe un juego de adivinar números del 1 al 100"],
            ],
            inputs=txt,
        )

        # Eventos
        btn.click(chat, inputs=[txt, chatbot], outputs=[txt, chatbot])
        txt.submit(chat, inputs=[txt, chatbot], outputs=[txt, chatbot])
        clear_btn.click(reset, outputs=[chatbot, chatbot])

    return demo


demo = create_chat_ui(
    client=bedrock,
    system=system,
    tools=tools,
    tools_schemas=all_schemas,
    sbx=sbx,
)

demo.launch(share=True, height=700)


# %% [markdown]
# ## 11. Chat CLI (alternativa sin Gradio)
# 
# Si prefieres una interfaz de texto simple en el notebook.
# Escribe `/salir` para terminar.
# 

# %%
# Descomenta para usar el chat de texto
print("Chat con el agente. Escribe '/salir' para terminar.\n")
messages = []
while True:
    query = input(">: ").strip()
    if query == "/salir":
        print("Sesión terminada.")
        break
    if not query:
        continue
    messages, _ = coding_agent(
        bedrock, query, system,
        tools=tools, tools_schemas=all_schemas,
        sbx=sbx, messages=messages,
    )


# %% [markdown]
# ## 12. Cerrar el sandbox
# 
# Cuando termines de usar el agente, cierra el sandbox para liberar recursos.
# 

# %%
# sbx.kill()
# print("Sandbox cerrado")


# %% [markdown]
# ---
# ## Resumen
# 
# | Componente | Tecnología | Rol |
# |---|---|---|
# | LLM | AWS Bedrock (Amazon Nova Pro) | Razonamiento y decisiones |
# | Ejecución de código | E2B Sandbox | Correr código de forma segura |
# | Herramientas | `execute_code`, `read_file`, `write_file` | Acciones del agente |
# | Interfaz | Gradio | UI de chat visual |
# | Loop | `max_steps` + detección sin tool calls | Control de flujo |
# 
# **Flujo completo:**
# ```
# Usuario → Gradio UI → coding_agent()
#    → llm() llama a Bedrock (Nova Pro)
#    → Bedrock decide qué tool usar
#    → execute_tool() ejecuta en E2B sandbox
#    → resultado vuelve al LLM como contexto
#    → loop hasta que no haya más tool calls
#    → respuesta final → Gradio UI → Usuario
# ```
# 


