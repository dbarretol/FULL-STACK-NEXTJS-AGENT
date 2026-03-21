# %% [markdown]
# # 🤓 Data Analyst Agent — AWS Bedrock + E2B + Gradio
# 
# Agente analista de datos  usando:
# - **AWS Bedrock** (Amazon Nova Pro) como LLM
# - **E2B** como sandbox seguro para ejecutar código y generar gráficas
# - **Gradio** como interfaz de chat visual con soporte de imágenes
# - **pokemon.csv** como dataset de ejemplo
# 
# > ⚠️ Guarda tus credenciales en **Colab Secrets** (🔑 candado en el panel izquierdo):
# > - `AWS_ACCESS_KEY_ID`
# > - `AWS_SECRET_ACCESS_KEY`
# > - `AWS_DEFAULT_REGION` (ej: `us-east-1`)
# > - `E2B_API_KEY`
# 

# %% [markdown]
# ## 1. Instalación

# %%
!pip install boto3 e2b-code-interpreter gradio -q


# %% [markdown]
# ## 2. Credenciales

# %%
import os, warnings
warnings.filterwarnings('ignore')
from google.colab import userdata

AWS_ACCESS_KEY_ID     = userdata.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = userdata.get("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION    = userdata.get("AWS_DEFAULT_REGION")
E2B_API_KEY           = userdata.get("E2B_API_KEY")

os.environ["E2B_API_KEY"] = E2B_API_KEY
print("✅ Credenciales cargadas")


# %% [markdown]
# ## 3. Cliente AWS Bedrock y función `llm`
# 
# Igual que en el notebook anterior: adaptamos los schemas OpenAI → Bedrock
# y normalizamos la respuesta con `_BedrockResponse`.
# 

# %%
import boto3, json

bedrock = boto3.client(
    service_name="bedrock-runtime",
    region_name=AWS_DEFAULT_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

MODEL_ID = "amazon.nova-pro-v1:0"


def _schema_to_bedrock(schema: dict) -> dict:
    return {
        "toolSpec": {
            "name": schema["name"],
            "description": schema.get("description", ""),
            "inputSchema": {"json": schema.get("parameters", {})},
        }
    }


def llm(client, messages, system, tools=None):
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
        self._raw         = raw
        self.output       = []
        self.output_text  = ""
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
        self.text = self.content = text


class _ToolUsePart:
    type = "function_call"
    def __init__(self, name, arguments, call_id):
        self.name = name
        self.arguments = arguments
        self.call_id = call_id


# Test rápido
resp = llm(bedrock, [{"role":"user","content":[{"text":"hola"}]}], "Responde muy breve en español.")
print(resp.output_text)


# %% [markdown]
# ## 4. Sandbox E2B y carga del dataset
# 
# Creamos el sandbox y subimos `pokemon.csv` como `data.csv`.
# El agente usará ese nombre para referirse al archivo en todo momento.
# 
# También instalamos `matplotlib` y `seaborn` dentro del sandbox
# para que el agente pueda generar gráficas.
# 

# %%
from e2b_code_interpreter import Sandbox
import os
from google.colab import files

sbx = Sandbox.create(timeout=60 * 60)
print(f"✅ Sandbox creado: {sbx.sandbox_id}")

# Subir el CSV desde tu ordenador
print("⏳ Por favor, sube tu archivo CSV...")
uploaded = files.upload()
if not uploaded:
    raise ValueError("No se ha subido ningún archivo.")

filename = list(uploaded.keys())[0]

# Leer el contenido del archivo subido
content = uploaded[filename]

# %%


sbx.files.write("data.csv", content.decode('utf-8'))
print(f"'{filename}' subido al sandbox como data.csv")

# Instalar librerías de visualización en el sandbox
setup_result = sbx.run_code(
    "import subprocess; subprocess.run(['pip','install','matplotlib','seaborn','pandas'], capture_output=True)"
)
print("Librerías de análisis instaladas en el sandbox")

# %% [markdown]
# ## 5. Herramienta `execute_code` con captura de imágenes
# 
# Esta es la diferencia clave respecto al agente de código básico:
# cuando el agente genera una gráfica con matplotlib/seaborn,
# E2B la captura como PNG en base64 dentro de `execution.results`.
# 
# Retornamos tanto el texto como las imágenes por separado,
# para que la UI de Gradio pueda mostrarlas.
# 

# %%
import base64
from typing import Callable, Optional, Dict, Any


def execute_code(sbx: Sandbox, code: str) -> tuple[dict, dict]:
    """
    Ejecuta código en E2B y retorna (resultado, metadata).
    metadata puede contener 'images' con PNGs en base64.
    """
    execution = sbx.run_code(code)

    results = []
    metadata = {}
    images   = []

    # Capturar resultados ricos (gráficas, dataframes, etc.)
    for r in execution.results:
        if hasattr(r, "png") and r.png:
            images.append(r.png)   # ya viene en base64
        if hasattr(r, "text") and r.text:
            results.append(r.text)

    if images:
        metadata["images"] = images

    # Capturar stdout / stderr
    logs   = list(execution.logs.stdout) if execution.logs.stdout else []
    errors = list(execution.logs.stderr) if execution.logs.stderr else []

    if execution.error:
        errors.append(f"{execution.error.name}: {execution.error.value}")

    return {"results": results, "logs": logs, "errors": errors}, metadata


# %% [markdown]
# Prueba: generar una gráfica desde el sandbox

# %%
test_code = """
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

df = pd.read_csv('data.csv')
print(f"Dataset cargado: {df.shape[0]} filas, {df.shape[1]} columnas")
print(df.dtypes.head())
"""

result, meta = execute_code(sbx, test_code)
print("Logs:", result["logs"])
print("Errores:", result["errors"])


# %% [markdown]
# ## 6. Schema de herramienta y `execute_tool`

# %%
execute_code_schema = {
    "type": "function",
    "name": "execute_code",
    "description": (
        "Ejecuta código Python en un sandbox seguro con pandas, matplotlib y seaborn disponibles. "
        "Usa matplotlib.use('Agg') antes de importar pyplot para generar gráficas. "
        "Retorna stdout, errores e imágenes generadas."
    ),
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

tools = {"execute_code": execute_code}
all_schemas = [execute_code_schema]


def execute_tool(name: str, args: str, tools: dict[str, Callable], **kwargs):
    """Ejecuta la herramienta y retorna (resultado, metadata)."""
    metadata = {}
    try:
        args_dict = json.loads(args)
        if name not in tools:
            return {"error": f"Herramienta '{name}' no existe."}, metadata
        result, metadata = tools[name](**args_dict, **kwargs)
    except json.JSONDecodeError as e:
        result = {"error": f"Error parseando argumentos: {str(e)}"}
    except Exception as e:
        result = {"error": str(e)}
    return result, metadata


# %% [markdown]
# ## 7. System prompt del agente analista
# 
# El system prompt le indica al agente que tiene un dataset `data.csv`
# y que su rol es explorar los datos y generar visualizaciones interesantes.
# 

# %%
system = """Eres un analista de datos Python senior experto.
Siempre usa la herramienta `execute_code` para ejecutar código.

El usuario ha subido un dataset llamado data.csv.
Tu trabajo es:
- Ayudar al usuario a entender los datos
- Crear visualizaciones interesantes y claras
- Responder preguntas sobre el dataset con análisis precisos

Para generar gráficas SIEMPRE usa:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import seaborn as sns

Responde siempre en español. Sé conciso pero completo.
"""


# %% [markdown]
# ## 8. Data Analyst Agent con loop
# 
# El agente itera ejecutando herramientas hasta completar la tarea.
# Retorna `(messages, last_text, all_images)` para que Gradio
# pueda mostrar tanto el texto como las gráficas generadas.
# 

# %%
def data_analyst_agent(
    client,
    query: str,
    system: str,
    tools: dict,
    tools_schemas: list,
    sbx: Sandbox,
    messages: list = None,
    max_steps: int = 10,
) -> tuple[list, str, list]:
    """
    Ejecuta el agente analista.
    Retorna (messages, respuesta_texto, lista_de_imagenes_base64)
    """
    if messages is None:
        messages = []

    messages.append({"role": "user", "content": [{"text": query}]})
    steps       = 0
    last_text   = ""
    all_images  = []

    while steps < max_steps:
        response = llm(client, messages, system, tools=tools_schemas)
        print(f"\n[paso #{steps}]")
        has_tool_call = False
        tool_results  = []

        messages.append(response.bedrock_message())

        for part in response.output:
            if part.type == "message":
                last_text = part.content
                print(f"[agente] {part.content[:200]}...")

            elif part.type == "function_call":
                has_tool_call = True
                name = part.name
                print(f"[agente][{name}] ejecutando...")
                result, metadata = execute_tool(name, part.arguments, tools, sbx=sbx)
                print(f"  logs:   {result.get('logs', [])[:3]}")
                print(f"  errors: {result.get('errors', [])}")

                # Capturar imágenes generadas
                if metadata.get("images"):
                    all_images.extend(metadata["images"])
                    print(f"  📊 {len(metadata['images'])} gráfica(s) generada(s)")

                tool_results.append({
                    "toolResult": {
                        "toolUseId": part.call_id,
                        "content":   [{"json": result}],
                    }
                })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        if not has_tool_call:
            print("\n[agente] ✅ análisis completado")
            break

        steps += 1
    else:
        print(f"\n[agente] ⚠️ límite de {max_steps} pasos alcanzado")

    return messages, last_text, all_images


# %% [markdown]
# ## 9. Pruebas directas (sin UI)

# %%
messages = []

messages, texto, imagenes = data_analyst_agent(
    bedrock,
    query="¿De qué trata este dataset? Dame un resumen general.",
    system=system,
    tools=tools,
    tools_schemas=all_schemas,
    sbx=sbx,
    messages=messages,
)
print("\n--- RESPUESTA ---")
print(texto)


# %%
# Mostrar imágenes si las hay
from IPython.display import Image, display
import base64

for img_b64 in imagenes:
    display(Image(data=base64.b64decode(img_b64)))


# %%
messages, texto, imagenes = data_analyst_agent(
    bedrock,
    query="Agrupa los pokémon por tipo primario y muestra cuántos hay de cada tipo en una gráfica de barras.",
    system=system,
    tools=tools,
    tools_schemas=all_schemas,
    sbx=sbx,
    messages=messages,   # ← mantiene el historial
)

for img_b64 in imagenes:
    display(Image(data=base64.b64decode(img_b64)))


# %% [markdown]
# ## 10. Interfaz Gradio con soporte de imágenes 📊
# 
# La UI muestra tanto las respuestas de texto como las gráficas generadas.
# El historial se mantiene entre mensajes (conversación continua).
# 

# %%
import gradio as gr
import base64
from PIL import Image as PILImage
import io


def pil_from_b64(b64_str: str) -> PILImage.Image:
    """Convierte base64 PNG a imagen PIL para Gradio."""
    img_bytes = base64.b64decode(b64_str)
    return PILImage.open(io.BytesIO(img_bytes))


def create_analyst_ui(client, system, tools, tools_schemas, sbx):
    conversation_messages = []

    def chat(user_message, chat_history, gallery_images):
        nonlocal conversation_messages

        conversation_messages, agent_reply, new_images = data_analyst_agent(
            client=client,
            query=user_message,
            system=system,
            tools=tools,
            tools_schemas=tools_schemas,
            sbx=sbx,
            messages=conversation_messages,
            max_steps=10,
        )

        # Agregar al chat
        chat_history.append((user_message, agent_reply))

        # Agregar nuevas imágenes a la galería
        for img_b64 in new_images:
            gallery_images.append(pil_from_b64(img_b64))

        return "", chat_history, gallery_images

    def reset():
        nonlocal conversation_messages
        conversation_messages = []
        return [], [], []

    with gr.Blocks(theme=gr.themes.Soft(), title="Data Analyst Agent 🤓") as demo:
        gr.Markdown("""
        # 🤓 Data Analyst Agent — AWS Bedrock + E2B
        Analiza el dataset `data.csv` haciendo preguntas en lenguaje natural.
        El agente ejecuta código Python en un sandbox seguro y genera visualizaciones.
        """)

        with gr.Row():
            with gr.Column(scale=6):
                chatbot = gr.Chatbot(
                    label="Conversación",
                    height=450,
                    bubble_full_width=False,
                )
                with gr.Row():
                    txt = gr.Textbox(
                        placeholder="Ej: ¿Cuáles son los pokémon legendarios más poderosos?",
                        label="Tu pregunta",
                        scale=9,
                    )
                    btn = gr.Button("Analizar ➤", variant="primary", scale=1)

            with gr.Column(scale=4):
                gallery = gr.Gallery(
                    label="📊 Gráficas generadas",
                    columns=1,
                    height=500,
                    object_fit="contain",
                )

        clear_btn = gr.Button("🗑️ Nueva conversación", variant="secondary")

        gr.Examples(
            examples=[
                ["¿De qué trata este dataset? Dame un resumen."],
                ["Agrupa los pokémon por tipo primario y muestra un gráfico de barras."],
                ["¿Cuáles son los 10 pokémon con mayor ataque total?"],
                ["Muestra la distribución de HP con un histograma."],
                ["¿Hay correlación entre el ataque y la defensa? Muestra un scatter plot."],
                ["¿Cuántos pokémon legendarios hay por generación?"],
                ["Compara las estadísticas promedio por tipo con un heatmap."],
            ],
            inputs=txt,
        )

        # Estado compartido
        gallery_state = gr.State([])

        btn.click(
            chat,
            inputs=[txt, chatbot, gallery_state],
            outputs=[txt, chatbot, gallery_state],
        ).then(
            lambda imgs: imgs,
            inputs=[gallery_state],
            outputs=[gallery],
        )

        txt.submit(
            chat,
            inputs=[txt, chatbot, gallery_state],
            outputs=[txt, chatbot, gallery_state],
        ).then(
            lambda imgs: imgs,
            inputs=[gallery_state],
            outputs=[gallery],
        )

        clear_btn.click(reset, outputs=[chatbot, gallery_state, gallery])

    return demo


demo = create_analyst_ui(
    client=bedrock,
    system=system,
    tools=tools,
    tools_schemas=all_schemas,
    sbx=sbx,
)

demo.launch(share=True, height=800)


# %% [markdown]
# ## 11. Tu turno — Analiza tu propio dataset
# 
# Sube cualquier CSV y el agente lo explorará por ti.
# 

# %%
from google.colab import files

# Subir tu propio archivo CSV
uploaded = files.upload()
filename = list(uploaded.keys())[0]

# Crear nuevo sandbox limpio para el nuevo dataset
sbx2 = Sandbox.create(timeout=60 * 60)
sbx2.run_code("import subprocess; subprocess.run(['pip','install','matplotlib','seaborn','pandas'], capture_output=True)")

with open(filename, "rb") as f:
    sbx2.files.write("data.csv", f.read())

print(f"✅ '{filename}' subido como data.csv")

# Lanzar UI con el nuevo dataset
demo2 = create_analyst_ui(
    client=bedrock,
    system=system,
    tools=tools,
    tools_schemas=all_schemas,
    sbx=sbx2,
)
demo2.launch(share=True, height=800)


# %% [markdown]
# ## 12. Cerrar sandboxes al terminar

# %%
# sbx.kill()
# print("✅ Sandbox principal cerrado")


# %% [markdown]
# ---
# ## ✅ Resumen
# 
# | Componente | Tecnología | Rol |
# |---|---|---|
# | LLM | AWS Bedrock (Amazon Nova Pro) | Razonamiento y análisis |
# | Ejecución de código | E2B Sandbox | Correr pandas/matplotlib de forma segura |
# | Captura de gráficas | E2B `execution.results[].png` | Extraer imágenes en base64 |
# | Interfaz | Gradio (chat + galería) | UI visual con historial e imágenes |
# 
# **Flujo del agente:**
# ```
# Usuario hace pregunta
#   → data_analyst_agent() → llm() → Bedrock (Nova Pro)
#   → Bedrock decide ejecutar código
#   → execute_code() corre pandas/matplotlib en E2B sandbox
#   → E2B retorna stdout + PNGs en base64
#   → Imágenes se muestran en Gradio Gallery
#   → Texto de análisis se muestra en el chat
#   → Loop hasta que no haya más tool calls
# ```
# 
