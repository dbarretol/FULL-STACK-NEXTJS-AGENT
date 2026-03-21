# 📋 WorkPackage.md — Agente de Código Full Stack

## 🎯 Objetivo General

Construir un **agente autónomo** que reciba instrucciones en lenguaje natural y genere
una aplicación web completa (Next.js), capaz de:

- Leer, escribir y buscar archivos en un sandbox E2B
- Ejecutar comandos de compilación/verificación
- Mantener conversaciones largas sin agotar el contexto del modelo
- Iterar sobre su propio código para corregir errores

**Stack tecnológico:**

| Componente         | Tecnología                     |
| ------------------ | ------------------------------ |
| LLM                | AWS Bedrock (Amazon Nova Pro)  |
| Sandbox            | E2B Code Interpreter           |
| Framework web      | Next.js (generado por agente)  |
| Interfaz           | Gradio (chat) o CLI            |
| Lenguaje           | Python (orquestación)          |

---

## 📁 Estructura del Proyecto

```
fullstack-agent/
├── WorkPackage.md              ← Este archivo
├── README.md                   ← Documentación del proyecto
├── requirements.txt            ← Dependencias Python
├── main.py                     ← Punto de entrada principal
├── lib/
│   ├── __init__.py
│   ├── bedrock_client.py       ← Cliente LLM + normalización Bedrock
│   ├── sbx_tools.py            ← Herramientas del filesystem (Parte 1)
│   ├── context_manager.py      ← Compresión de contexto (Parte 2)
│   ├── schemas.py              ← Schemas de todas las herramientas
│   ├── agent.py                ← Loop principal del agente (Parte 3-4)
│   └── prompts.py              ← System prompts
├── ui/
│   └── gradio_app.py           ← Interfaz Gradio (opcional)
├── tests/
│   ├── test_tools.py           ← Tests de herramientas
│   ├── test_compression.py     ← Tests de compresión
│   └── test_agent.py           ← Tests de integración
├── screenshots/
│   ├── app_before.png          ← Captura antes del ajuste
│   └── app_after.png           ← Captura después del ajuste
└── .env.example                ← Plantilla de variables de entorno
```

---

## 🔢 Fases de Desarrollo

---

### FASE 0 — Setup e Infraestructura Base

**Duración estimada:** 30-45 min

#### Tareas

| #   | Tarea                                            | Estado |
| --- | ------------------------------------------------ | ------ |
| 0.1 | Crear estructura de carpetas del proyecto        | ⬜     |
| 0.2 | Crear `requirements.txt`                         | ⬜     |
| 0.3 | Configurar credenciales (`.env` o Colab Secrets) | ⬜     |
| 0.4 | Copiar y adaptar `bedrock_client.py` del ejemplo | ⬜     |
| 0.5 | Verificar conexión a Bedrock con test "hola"     | ⬜     |
| 0.6 | Verificar creación de sandbox E2B                | ⬜     |

#### Archivo: `requirements.txt`

```
boto3
e2b-code-interpreter
gradio
Pillow
```

#### Archivo: `lib/bedrock_client.py`

Reutilizar del ejemplo anterior:

```python
# Copiar:
#   - _schema_to_bedrock()
#   - llm()
#   - _BedrockResponse
#   - _TextPart
#   - _ToolUsePart
#
# Agregar:
#   - inferenceConfig con temperature=0.2, maxTokens=4096
#   - Manejo de excepciones en llm()
```

**Criterio de aceptación:**

- [x] `llm()` responde correctamente a un mensaje de prueba
- [x] `Sandbox.create()` retorna un sandbox_id válido

---

### FASE 1 — Herramientas del Sistema de Archivos

**Duración estimada:** 2-3 horas

**Archivo principal:** `lib/sbx_tools.py`

---

#### 1.0 — Clase `ToolError`

```python
class ToolError(Exception):
    """Error controlado de herramienta. El mensaje se envía al LLM."""
    pass
```

**Propósito:** Separar errores esperados (archivo no existe) de errores
inesperados (crash). El agente puede recuperarse de un `ToolError`.

---

#### 1.1 — `execute_code(sbx, code) → dict`

| Campo    | Descripción                         |
| -------- | ----------------------------------- |
| Input    | `code: str` — código Python a correr |
| Output   | `{"stdout", "stderr", "error", "success": bool}` |
| Sandbox  | Ejecuta via `sbx.run_code(code)`    |

**Implementación:**

```python
def execute_code(sbx: Sandbox, code: str) -> dict:
    """
    Ejecuta código Python en el sandbox E2B.
    Retorna dict con stdout, stderr, error y flag success.
    """
    execution = sbx.run_code(code)
    
    stdout = execution.logs.stdout if execution.logs.stdout else []
    stderr = execution.logs.stderr if execution.logs.stderr else []
    
    error = None
    if execution.error:
        error = f"{execution.error.name}: {execution.error.value}"
    
    results = []
    for r in execution.results:
        if hasattr(r, "text") and r.text:
            results.append(r.text)
    
    return {
        "stdout": stdout,
        "stderr": stderr,
        "results": results,
        "error": error,
        "success": error is None
    }
```

**Tests:**

```python
# Test OK
result = execute_code(sbx, "print('hello')")
assert result["success"] == True
assert "hello" in result["stdout"]

# Test error
result = execute_code(sbx, "1/0")
assert result["success"] == False
assert "ZeroDivision" in result["error"]
```

---

#### 1.2 — `list_directory(sbx, path) → dict`

| Campo    | Descripción                                        |
| -------- | -------------------------------------------------- |
| Input    | `path: str` — ruta del directorio (default: ".")   |
| Output   | `{"entries": [{"name", "type", "size"}], "count"}` |
| Errores  | `ToolError` si la ruta no existe                    |

**Implementación guía:**

```python
def list_directory(sbx: Sandbox, path: str = ".") -> dict:
    """Lista archivos y carpetas en el path dado."""
    code = f"""
import os, json
path = {repr(path)}
if not os.path.isdir(path):
    print(json.dumps({{"error": f"Directorio '{{path}}' no existe"}}))
else:
    entries = []
    for name in sorted(os.listdir(path)):
        full = os.path.join(path, name)
        entry = {{
            "name": name,
            "type": "dir" if os.path.isdir(full) else "file",
            "size": os.path.getsize(full) if os.path.isfile(full) else None
        }}
        entries.append(entry)
    print(json.dumps({{"entries": entries, "count": len(entries)}}))
"""
    result = execute_code(sbx, code)
    
    if not result["success"]:
        raise ToolError(f"Error listando {path}: {result['error']}")
    
    try:
        output = json.loads("".join(result["stdout"]))
        if "error" in output:
            raise ToolError(output["error"])
        return output
    except json.JSONDecodeError:
        raise ToolError(f"Output inesperado: {''.join(result['stdout'])}")
```

**Tests:**

```python
# Setup: crear archivos de prueba
execute_code(sbx, "open('test.txt','w').write('hola')")
execute_code(sbx, "os.makedirs('subdir', exist_ok=True)")

result = list_directory(sbx, ".")
assert result["count"] > 0
assert any(e["name"] == "test.txt" for e in result["entries"])

# Test error
try:
    list_directory(sbx, "/no/existe")
    assert False, "Debería lanzar ToolError"
except ToolError:
    pass
```

---

#### 1.3 — `read_file(sbx, path, limit, offset) → dict`

| Campo    | Descripción                                       |
| -------- | ------------------------------------------------- |
| Input    | `path: str`, `limit: int = None`, `offset: int = 0` |
| Output   | `{"content": str, "size": int, "truncated": bool}` |
| Errores  | `ToolError` si el archivo no existe                |

**Notas de implementación:**

- Manejar `limit=0` correctamente (NO como falsy — bug del ejemplo anterior)
- Incluir flag `truncated` para que el agente sepa si hay más contenido
- Limitar lectura máxima a 50,000 caracteres como safety net

```python
MAX_READ_SIZE = 50_000

def read_file(sbx: Sandbox, path: str,
              limit: int = None, offset: int = 0) -> dict:
    """Lee contenido de un archivo del sandbox."""
    effective_limit = limit if limit is not None else MAX_READ_SIZE
    
    code = f"""
import os, json
path = {repr(path)}
if not os.path.isfile(path):
    print(json.dumps({{"error": f"Archivo '{{path}}' no existe"}}))
else:
    size = os.path.getsize(path)
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        f.seek({offset})
        content = f.read({effective_limit})
    truncated = ({offset} + len(content)) < size
    print(json.dumps({{
        "content": content,
        "size": size,
        "truncated": truncated
    }}))
"""
    result = execute_code(sbx, code)
    
    if not result["success"]:
        raise ToolError(f"Error leyendo {path}: {result['error']}")
    
    output = json.loads("".join(result["stdout"]))
    if "error" in output:
        raise ToolError(output["error"])
    return output
```

---

#### 1.4 — `write_file(sbx, path, content) → dict`

| Campo    | Descripción                                       |
| -------- | ------------------------------------------------- |
| Input    | `path: str`, `content: str`                       |
| Output   | `{"message": str, "bytes_written": int}`          |
| Errores  | `ToolError` si falla la escritura                  |

**Notas de implementación:**

- Crear directorios intermedios automáticamente
- Retornar bytes escritos para confirmación
- Validar que `content` no sea excesivamente grande (>1MB)

```python
MAX_WRITE_SIZE = 1_000_000  # 1MB

def write_file(sbx: Sandbox, path: str, content: str) -> dict:
    """Escribe contenido en un archivo del sandbox."""
    if len(content) > MAX_WRITE_SIZE:
        raise ToolError(f"Contenido demasiado grande: {len(content)} chars (max {MAX_WRITE_SIZE})")
    
    # Usar sbx.files.write() directamente — más seguro que generar código
    try:
        sbx.files.write(path, content)
        return {
            "message": f"Archivo '{path}' escrito correctamente",
            "bytes_written": len(content.encode('utf-8'))
        }
    except Exception as e:
        raise ToolError(f"Error escribiendo {path}: {str(e)}")
```

**⚠️ Decisión de diseño:**
Usar `sbx.files.write()` directo en vez de generar código Python con `repr(content)`.

Razón: si `content` contiene código con comillas, backslashes, etc.,
generar código que lo inyecte como string literal es frágil y propenso a errores.

---

#### 1.5 — `search_file_content(sbx, pattern, path, max_results) → dict`

| Campo    | Descripción                                       |
| -------- | ------------------------------------------------- |
| Input    | `pattern: str`, `path: str = "."`, `max_results: int = 20` |
| Output   | `{"matches": [{"file", "line", "content"}], "total", "truncated"}` |

**Implementación guía:**

```python
def search_file_content(sbx: Sandbox, pattern: str,
                        path: str = ".", max_results: int = 20) -> dict:
    """Busca un patrón de texto en archivos del sandbox."""
    code = f"""
import os, json, re

pattern = {repr(pattern)}
root = {repr(path)}
max_results = {max_results}
matches = []
total = 0

for dirpath, _, filenames in os.walk(root):
    # Ignorar node_modules, .next, .git
    if any(skip in dirpath for skip in ['node_modules', '.next', '.git', '__pycache__']):
        continue
    for fname in filenames:
        # Solo archivos de texto
        if not fname.endswith(('.js','.jsx','.ts','.tsx','.css','.html','.json','.md','.py','.txt','.env')):
            continue
        fpath = os.path.join(dirpath, fname)
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    if pattern.lower() in line.lower():
                        total += 1
                        if len(matches) < max_results:
                            matches.append({{
                                "file": fpath,
                                "line": i,
                                "content": line.strip()[:200]
                            }})
        except:
            pass

print(json.dumps({{
    "matches": matches,
    "total": total,
    "truncated": total > max_results
}}))
"""
    result = execute_code(sbx, code)
    if not result["success"]:
        raise ToolError(f"Error buscando '{pattern}': {result['error']}")
    
    return json.loads("".join(result["stdout"]))
```

---

#### 1.6 (Opcional) — `replace_in_file(sbx, path, old, new) → dict`

| Campo    | Descripción                                       |
| -------- | ------------------------------------------------- |
| Input    | `path: str`, `old: str`, `new: str`               |
| Output   | `{"replacements": int, "message": str}`           |

**Implementación sugerida:**

```python
def replace_in_file(sbx: Sandbox, path: str, old: str, new: str) -> dict:
    """Reemplaza todas las ocurrencias de 'old' por 'new' en un archivo."""
    # Leer
    file_data = read_file(sbx, path)
    content = file_data["content"]
    
    count = content.count(old)
    if count == 0:
        raise ToolError(f"Patrón '{old[:50]}...' no encontrado en {path}")
    
    new_content = content.replace(old, new)
    write_file(sbx, path, new_content)
    
    return {
        "replacements": count,
        "message": f"{count} reemplazo(s) en {path}"
    }
```

---

#### 1.7 (Opcional) — `glob_files(sbx, pattern) → dict`

```python
def glob_files(sbx: Sandbox, pattern: str) -> dict:
    """Busca archivos por nombre/extensión usando glob."""
    code = f"""
import glob, json
files = glob.glob({repr(pattern)}, recursive=True)
# Filtrar node_modules
files = [f for f in files if 'node_modules' not in f and '.next' not in f]
print(json.dumps({{"files": files[:100], "total": len(files)}}))
"""
    result = execute_code(sbx, code)
    if not result["success"]:
        raise ToolError(f"Error en glob '{pattern}': {result['error']}")
    return json.loads("".join(result["stdout"]))
```

---

#### 1.8 — `execute_tool()` dispatcher

```python
def execute_tool(name: str, args: str, tools_map: dict, **kwargs) -> dict:
    """
    Dispatcher central de herramientas.
    Maneja ToolError como resultado controlado.
    """
    try:
        args_dict = json.loads(args)
    except json.JSONDecodeError as e:
        return {"error": f"JSON inválido: {e}"}
    
    if name not in tools_map:
        return {"error": f"Herramienta '{name}' no existe"}
    
    try:
        return tools_map[name](**args_dict, **kwargs)
    except ToolError as e:
        return {"error": str(e)}  # Error controlado → el agente puede reintentar
    except Exception as e:
        return {"error": f"Error inesperado en {name}: {str(e)}"}
```

---

#### 1.9 — Schemas

**Archivo:** `lib/schemas.py`

```python
TOOL_SCHEMAS = [
    {
        "type": "function",
        "name": "execute_code",
        "description": "Ejecuta código Python o comandos shell en el sandbox.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Código Python a ejecutar"}
            },
            "required": ["code"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "list_directory",
        "description": "Lista archivos y carpetas en un directorio del sandbox.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Ruta del directorio", "default": "."}
            },
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "read_file",
        "description": "Lee el contenido de un archivo. Retorna content, size y si fue truncado.",
        "parameters": {
            "type": "object",
            "properties": {
                "path":   {"type": "string", "description": "Ruta del archivo"},
                "limit":  {"type": "integer", "description": "Máx caracteres a leer"},
                "offset": {"type": "integer", "description": "Posición de inicio", "default": 0}
            },
            "required": ["path"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "write_file",
        "description": "Escribe contenido en un archivo. Crea directorios si no existen.",
        "parameters": {
            "type": "object",
            "properties": {
                "path":    {"type": "string", "description": "Ruta del archivo"},
                "content": {"type": "string", "description": "Contenido a escribir"}
            },
            "required": ["path", "content"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "search_file_content",
        "description": "Busca un patrón de texto en todos los archivos del proyecto.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern":     {"type": "string", "description": "Texto a buscar"},
                "path":        {"type": "string", "description": "Directorio raíz", "default": "."},
                "max_results": {"type": "integer", "description": "Máximo de resultados", "default": 20}
            },
            "required": ["pattern"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "replace_in_file",
        "description": "Reemplaza todas las ocurrencias de un texto por otro en un archivo.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Ruta del archivo"},
                "old":  {"type": "string", "description": "Texto a buscar"},
                "new":  {"type": "string", "description": "Texto de reemplazo"}
            },
            "required": ["path", "old", "new"],
            "additionalProperties": False
        }
    }
]
```

---

**✅ Criterios de aceptación Fase 1:**

- [ ] Todas las herramientas ejecutan en E2B sin errores
- [ ] `ToolError` se propaga correctamente al agente
- [ ] Tests unitarios pasan para cada herramienta
- [ ] `execute_tool()` dispatcher maneja todos los casos

---

### FASE 2 — Compresión de Contexto (Runtime Summary)

**Duración estimada:** 1.5-2 horas

**Archivo:** `lib/context_manager.py`

---

#### 2.1 — Entender el Problema

```
Mensaje 1:  user → "Crea app Next.js"
Mensaje 2:  assistant → tool_call (execute_code: npx create-next-app)
Mensaje 3:  user → tool_result (stdout: 500 líneas)
Mensaje 4:  assistant → tool_call (write_file: page.tsx)
Mensaje 5:  user → tool_result (ok)
...
Mensaje 40: assistant → "Listo, tu app está creada"
```

Cada mensaje consume tokens. Con 40 pasos fácilmente llegas a 40,000+ tokens.

El modelo tiene límite. Debes comprimir para seguir operando.

---

#### 2.2 — Constantes

```python
MAX_TOKENS = 40_000          # Límite antes de comprimir
COMPRESSION_RATIO = 0.70     # Comprimir el 70% más antiguo
CHARS_PER_TOKEN = 4          # Aproximación: 1 token ≈ 4 caracteres
```

---

#### 2.3 — `count_tokens(messages) → int`

```python
def count_tokens(messages: list) -> int:
    """
    Estimación de tokens basada en caracteres.
    Para producción usar tiktoken o la API de Bedrock.
    """
    total_chars = 0
    for msg in messages:
        for content_block in msg.get("content", []):
            if isinstance(content_block, dict):
                if "text" in content_block:
                    total_chars += len(content_block["text"])
                elif "toolResult" in content_block:
                    # Serializar el resultado para contar
                    total_chars += len(json.dumps(content_block["toolResult"]))
                elif "toolUse" in content_block:
                    total_chars += len(json.dumps(content_block["toolUse"]))
    return total_chars // CHARS_PER_TOKEN
```

**Tests:**

```python
msgs = [{"role": "user", "content": [{"text": "hola mundo"}]}]  # 10 chars
assert count_tokens(msgs) == 2  # 10 // 4 = 2
```

---

#### 2.4 — `compress_context(messages, llm_client) → list`

**Algoritmo:**

```
1. Calcular split_point = int(len(messages) * COMPRESSION_RATIO)
2. old_messages = messages[:split_point]
3. recent_messages = messages[split_point:]
4. Generar resumen de old_messages usando el LLM
5. Crear mensaje sintético con el resumen
6. Retornar [resumen] + recent_messages
```

**Implementación:**

```python
SUMMARY_SYSTEM = """Eres un asistente que resume conversaciones técnicas.
Resume la siguiente conversación entre un usuario y un agente de código.
Incluye:
- Qué archivos se crearon/modificaron
- Qué comandos se ejecutaron
- Qué errores hubo y cómo se resolvieron
- Estado actual del proyecto
Sé conciso pero no pierdas información crítica sobre la estructura del proyecto."""


def compress_context(messages: list, llm_client) -> list:
    """
    Comprime el 70% más antiguo de los mensajes en un resumen.
    Retorna lista reducida de mensajes.
    """
    if len(messages) < 4:
        return messages  # No comprimir conversaciones cortas
    
    split_point = int(len(messages) * COMPRESSION_RATIO)
    
    # Asegurar que split_point cae en un número par (user/assistant)
    # para no cortar a mitad de un intercambio
    if split_point % 2 != 0:
        split_point += 1
    
    old_messages = messages[:split_point]
    recent_messages = messages[split_point:]
    
    # Serializar mensajes antiguos para el resumen
    conversation_text = _serialize_messages_for_summary(old_messages)
    
    # Pedir resumen al LLM
    summary_messages = [
        {"role": "user", "content": [{"text": f"Resume esta conversación:\n\n{conversation_text}"}]}
    ]
    
    response = llm(llm_client, summary_messages, SUMMARY_SYSTEM)
    summary_text = response.output_text
    
    # Crear mensajes sintéticos con el resumen
    compressed = [
        {
            "role": "user",
            "content": [{"text": f"[RESUMEN DE CONVERSACIÓN ANTERIOR]\n{summary_text}"}]
        },
        {
            "role": "assistant",
            "content": [{"text": "Entendido. Tengo el contexto de lo que hicimos anteriormente. ¿En qué continúo?"}]
        }
    ]
    
    return compressed + recent_messages


def _serialize_messages_for_summary(messages: list) -> str:
    """Convierte mensajes a texto legible para el LLM de resumen."""
    lines = []
    for msg in messages:
        role = msg["role"]
        for block in msg.get("content", []):
            if isinstance(block, dict):
                if "text" in block:
                    lines.append(f"[{role}]: {block['text'][:500]}")
                elif "toolUse" in block:
                    tu = block["toolUse"]
                    code_preview = json.dumps(tu.get("input", {}))[:300]
                    lines.append(f"[{role}][tool:{tu['name']}]: {code_preview}")
                elif "toolResult" in block:
                    tr = block["toolResult"]
                    result_preview = json.dumps(tr.get("content", []))[:300]
                    lines.append(f"[{role}][result]: {result_preview}")
    return "\n".join(lines)
```

---

#### 2.5 — `maybe_compress(messages, llm_client) → list`

```python
def maybe_compress(messages: list, llm_client) -> list:
    """
    Verifica si el contexto excede MAX_TOKENS.
    Si sí, comprime. Si no, retorna sin cambios.
    """
    current_tokens = count_tokens(messages)
    
    if current_tokens > MAX_TOKENS:
        print(f"⚠️ Contexto: {current_tokens} tokens > {MAX_TOKENS}. Comprimiendo...")
        compressed = compress_context(messages, llm_client)
        new_tokens = count_tokens(compressed)
        print(f"✅ Comprimido: {current_tokens} → {new_tokens} tokens")
        return compressed
    
    return messages
```

---

**✅ Criterios de aceptación Fase 2:**

- [ ] `count_tokens()` estima correctamente (±20%)
- [ ] `compress_context()` reduce mensajes manteniendo información crítica
- [ ] `maybe_compress()` solo actúa cuando se supera el umbral
- [ ] El resumen preserva: archivos creados, estructura del proyecto, último estado
- [ ] No se rompe el formato de mensajes Bedrock después de comprimir

---

### FASE 3 — System Prompt para Web Dev Agent

**Duración estimada:** 1 hora

**Archivo:** `lib/prompts.py`

---

#### 3.1 — Diseñar el prompt

El prompt debe cubrir:

1. **Identidad:** Eres un desarrollador Full Stack senior
2. **Stack:** Next.js 14+ con App Router, TypeScript, Tailwind CSS
3. **Proceso de razonamiento:** Pensar antes de actuar
4. **Herramientas:** Cuándo usar cada una
5. **Verificación:** Siempre comprobar que compila
6. **Estilo:** Código limpio, modular, bien comentado

```python
SYSTEM_PROMPT_WEB_DEV = """Eres un desarrollador web Full Stack senior experto.

## Tu Stack
- Next.js 14+ con App Router
- TypeScript
- Tailwind CSS
- React Server Components donde sea posible

## Proceso de Trabajo
1. **ANALIZAR**: Antes de escribir código, analiza qué se necesita.
   Usa `list_directory` y `read_file` para entender el estado actual.
2. **PLANIFICAR**: Describe brevemente qué archivos vas a crear/modificar.
3. **IMPLEMENTAR**: Usa `write_file` para crear/editar archivos.
   Escribe archivos COMPLETOS, no fragmentos.
4. **VERIFICAR**: Después de escribir, ejecuta `npx next build` o `npx tsc --noEmit`
   para verificar que no hay errores de compilación.
5. **CORREGIR**: Si hay errores, léelos, identifica la causa y corrige.

## Herramientas Disponibles
- `execute_code`: Para instalar dependencias (npm install), ejecutar builds,
  correr comandos shell. Envuelve comandos shell con subprocess o !.
- `list_directory`: Para ver qué archivos existen antes de modificar.
- `read_file`: Para leer código existente antes de editarlo.
- `write_file`: Para crear o sobrescribir archivos completos.
- `search_file_content`: Para encontrar dónde se usa un componente/función/estilo.
- `replace_in_file`: Para cambios puntuales en archivos existentes.

## Reglas Importantes
- SIEMPRE escribe archivos COMPLETOS con `write_file`. No uses diffs parciales.
- SIEMPRE verifica compilación después de cambios importantes.
- Si un build falla, lee el error completo y corrige antes de continuar.
- Para crear un proyecto nuevo, usa: `npx create-next-app@latest app --typescript --tailwind --eslint --app --no-src-dir --import-alias "@/*" --yes`
- Trabaja dentro del directorio `app/`.
- Responde en español.
- Sé conciso en explicaciones pero completo en código.

## Estructura Típica Next.js
```
app/
├── layout.tsx      ← Layout raíz
├── page.tsx        ← Página principal
├── globals.css     ← Estilos globales
├── components/     ← Componentes reutilizables
│   └── ...
├── lib/            ← Utilidades
│   └── ...
└── public/         ← Assets estáticos
```

Cuando el usuario pida cambios sobre una app existente, PRIMERO lee los archivos
relevantes para entender el estado actual, LUEGO modifica.
"""
```

---

**✅ Criterios de aceptación Fase 3:**

- [ ] El prompt guía al agente a usar herramientas correctamente
- [ ] El agente verifica compilación después de cambios
- [ ] El agente lee archivos antes de modificarlos
- [ ] El agente crea proyectos Next.js funcionales

---

### FASE 4 — Loop del Agente con Compresión

**Duración estimada:** 2-3 horas

**Archivo:** `lib/agent.py`

---

#### 4.1 — Función `run_agent()`

```python
from lib.bedrock_client import llm
from lib.sbx_tools import execute_tool, tools_map
from lib.context_manager import maybe_compress
from lib.schemas import TOOL_SCHEMAS
from lib.prompts import SYSTEM_PROMPT_WEB_DEV


def run_agent(
    client,
    query: str,
    sbx,
    messages: list = None,
    system: str = SYSTEM_PROMPT_WEB_DEV,
    tools: dict = None,
    tools_schemas: list = None,
    max_steps: int = 30,      # Web dev necesita más pasos
) -> tuple[list, str]:
    """
    Ejecuta el agente Full Stack con compresión de contexto.
    
    Args:
        client: Cliente Bedrock
        query: Instrucción del usuario
        sbx: Sandbox E2B
        messages: Historial (se modifica in-place)
        system: System prompt
        tools: Mapa nombre→función
        tools_schemas: Schemas de herramientas
        max_steps: Límite de iteraciones
    
    Returns:
        (messages_actualizados, respuesta_final)
    """
    if messages is None:
        messages = []
    if tools is None:
        tools = tools_map
    if tools_schemas is None:
        tools_schemas = TOOL_SCHEMAS
    
    # Agregar query del usuario
    messages.append({"role": "user", "content": [{"text": query}]})
    
    steps = 0
    last_text = ""
    
    while steps < max_steps:
        # --- COMPRESIÓN DE CONTEXTO ---
        messages = maybe_compress(messages, client)
        
        # --- LLAMADA AL LLM ---
        response = llm(client, messages, system, tools=tools_schemas)
        
        print(f"\n{'='*60}")
        print(f"  PASO #{steps}")
        print(f"{'='*60}")
        
        has_tool_call = False
        tool_results = []
        
        # Agregar respuesta del asistente al historial
        messages.append(response.bedrock_message())
        
        for part in response.output:
            if part.type == "message":
                last_text = part.content
                # Mostrar primeros 200 chars
                preview = part.content[:200]
                print(f"  💬 {preview}{'...' if len(part.content) > 200 else ''}")
            
            elif part.type == "function_call":
                has_tool_call = True
                name = part.name
                
                # Preview de argumentos
                try:
                    args_preview = json.loads(part.arguments)
                    if name in ("write_file",):
                        # No imprimir contenido completo
                        preview = {k: (v[:80]+"..." if isinstance(v,str) and len(v)>80 else v) 
                                   for k,v in args_preview.items()}
                    else:
                        preview = args_preview
                except:
                    preview = part.arguments[:100]
                
                print(f"  🔧 [{name}] {json.dumps(preview, ensure_ascii=False)[:200]}")
                
                # Ejecutar herramienta
                result = execute_tool(name, part.arguments, tools, sbx=sbx)
                
                # Preview de resultado
                if result.get("error"):
                    print(f"  ❌ Error: {result['error'][:150]}")
                else:
                    result_preview = json.dumps(result, ensure_ascii=False)[:150]
                    print(f"  ✅ {result_preview}")
                
                tool_results.append({
                    "toolResult": {
                        "toolUseId": part.call_id,
                        "content": [{"json": result}]
                    }
                })
        
        # Agregar resultados de herramientas
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        
        # Terminar si no hubo tool calls
        if not has_tool_call:
            print(f"\n{'='*60}")
            print(f"  ✅ TAREA COMPLETADA en {steps} pasos")
            print(f"{'='*60}")
            break
        
        steps += 1
    else:
        print(f"\n⚠️ Límite de {max_steps} pasos alcanzado")
    
    return messages, last_text
```

---

#### 4.2 — Setup del Sandbox para Next.js

```python
def setup_nextjs_sandbox(sbx):
    """Prepara el sandbox con Node.js y dependencias base."""
    print("⏳ Configurando sandbox para Next.js...")
    
    # Verificar Node.js
    result = execute_code(sbx, """
import subprocess
result = subprocess.run(['node', '--version'], capture_output=True, text=True)
print(f"Node.js: {result.stdout.strip()}")
result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
print(f"npm: {result.stdout.strip()}")
""")
    print("  " + "\n  ".join(result.get("stdout", [])))
    
    # Si Node no está disponible, instalarlo
    # (E2B ya trae Node.js por defecto en la mayoría de imágenes)
    
    print("✅ Sandbox listo para Next.js")
```

---

#### 4.3 — Pruebas del Agente

```python
# === PRUEBA 1: Crear app ===
historial = []

historial, respuesta = run_agent(
    client=bedrock,
    query="Crea una app de lista de tareas estilo Windows 95. "
          "Debe tener una barra de título, botones con estilo retro, "
          "y funcionalidad para agregar y eliminar tareas.",
    sbx=sbx,
    messages=historial,
    max_steps=30,
)

print("\n\n📝 RESPUESTA FINAL:")
print(respuesta)

# >>> CAPTURA: screenshots/app_before.png


# === PRUEBA 2: Corregir sobre misma conversación ===
historial, respuesta = run_agent(
    client=bedrock,
    query="Los íconos del nav son blancos y no se ven. Arreglalos. "
          "Ponles un color oscuro que contraste bien.",
    sbx=sbx,
    messages=historial,  # ← MISMO historial
    max_steps=15,
)

print("\n\n📝 RESPUESTA FINAL:")
print(respuesta)

# >>> CAPTURA: screenshots/app_after.png
```

---

**✅ Criterios de aceptación Fase 4:**

- [ ] El agente crea un proyecto Next.js funcional
- [ ] El agente verifica compilación (`next build` o `tsc`)
- [ ] Si hay errores, el agente los lee y corrige
- [ ] La compresión se activa automáticamente en conversaciones largas
- [ ] La segunda tarea usa el historial de la primera
- [ ] Capturas antes/después muestran el cambio

---

### FASE 5 — Interfaz Gradio (Opcional pero Recomendada)

**Duración estimada:** 1-2 horas

**Archivo:** `ui/gradio_app.py`

```python
import gradio as gr


def create_fullstack_ui(client, system, tools, tools_schemas, sbx):
    conversation_messages = []
    
    def chat(user_message, chat_history):
        nonlocal conversation_messages
        
        conversation_messages, agent_reply = run_agent(
            client=client,
            query=user_message,
            sbx=sbx,
            messages=conversation_messages,
            system=system,
            tools=tools,
            tools_schemas=tools_schemas,
            max_steps=30,
        )
        
        chat_history.append((user_message, agent_reply))
        return "", chat_history
    
    def reset():
        nonlocal conversation_messages
        conversation_messages = []
        return [], []
    
    with gr.Blocks(theme=gr.themes.Soft(), title="Full Stack Agent 🏗️") as demo:
        gr.Markdown("""
        # 🏗️ Full Stack Code Agent — AWS Bedrock + E2B
        Describe una app web y el agente la construye con Next.js + TypeScript + Tailwind.
        """)
        
        chatbot = gr.Chatbot(label="Conversación", height=550, bubble_full_width=False)
        
        with gr.Row():
            txt = gr.Textbox(
                placeholder="Ej: Crea una app de notas estilo Apple Notes",
                label="Tu instrucción",
                scale=9,
            )
            btn = gr.Button("Construir ➤", variant="primary", scale=1)
        
        clear_btn = gr.Button("🗑️ Nuevo proyecto", variant="secondary")
        
        gr.Examples(
            examples=[
                ["Crea una app de lista de tareas estilo Windows 95"],
                ["Crea un dashboard con cards que muestren estadísticas ficticias"],
                ["Crea un portfolio personal minimalista con secciones About, Projects y Contact"],
                ["Crea un clon simple de Twitter con feed de posts estáticos"],
            ],
            inputs=txt,
        )
        
        btn.click(chat, [txt, chatbot], [txt, chatbot])
        txt.submit(chat, [txt, chatbot], [txt, chatbot])
        clear_btn.click(reset, outputs=[chatbot, chatbot])
    
    return demo
```

---

### FASE 6 — Testing y Documentación

**Duración estimada:** 1-2 horas

---

#### 6.1 — Tests

**Archivo:** `tests/test_tools.py`

```python
"""Tests para herramientas del sandbox."""

def test_execute_code_success(sbx):
    result = execute_code(sbx, "print(2+2)")
    assert result["success"]
    assert "4" in result["stdout"]

def test_execute_code_error(sbx):
    result = execute_code(sbx, "raise ValueError('test')")
    assert not result["success"]

def test_write_and_read_file(sbx):
    write_file(sbx, "/tmp/test.txt", "hello world")
    data = read_file(sbx, "/tmp/test.txt")
    assert data["content"] == "hello world"

def test_list_directory(sbx):
    write_file(sbx, "/tmp/testdir/a.txt", "a")
    result = list_directory(sbx, "/tmp/testdir")
    assert result["count"] == 1

def test_search_file_content(sbx):
    write_file(sbx, "/tmp/search_test.txt", "foo bar baz\nhello world")
    result = search_file_content(sbx, "hello", path="/tmp")
    assert result["total"] >= 1

def test_replace_in_file(sbx):
    write_file(sbx, "/tmp/replace.txt", "old text here")
    replace_in_file(sbx, "/tmp/replace.txt", "old", "new")
    data = read_file(sbx, "/tmp/replace.txt")
    assert "new text here" in data["content"]

def test_tool_error_on_missing_file(sbx):
    try:
        read_file(sbx, "/nonexistent/file.txt")
        assert False
    except ToolError:
        pass
```

**Archivo:** `tests/test_compression.py`

```python
"""Tests para compresión de contexto."""

def test_count_tokens():
    msgs = [{"role":"user","content":[{"text":"a"*400}]}]
    tokens = count_tokens(msgs)
    assert tokens == 100  # 400 / 4

def test_maybe_compress_under_limit():
    msgs = [{"role":"user","content":[{"text":"hola"}]}]
    result = maybe_compress(msgs, mock_client)
    assert result == msgs  # Sin cambios

def test_compress_reduces_messages():
    # Crear 40 mensajes largos que superen MAX_TOKENS
    msgs = []
    for i in range(40):
        msgs.append({"role":"user","content":[{"text":f"Mensaje largo #{i} " + "x"*1000}]})
        msgs.append({"role":"assistant","content":[{"text":f"Respuesta #{i} " + "y"*1000}]})
    
    compressed = compress_context(msgs, mock_client)
    assert len(compressed) < len(msgs)
```

---

#### 6.2 — README.md

```markdown
# 🏗️ Full Stack Code Agent

Agente autónomo que genera aplicaciones web completas
a partir de instrucciones en lenguaje natural.

## Stack
- **LLM:** AWS Bedrock (Amazon Nova Pro)
- **Sandbox:** E2B Code Interpreter
- **Framework generado:** Next.js 14 + TypeScript + Tailwind
- **UI:** Gradio

## Características
- ✅ Genera apps Next.js completas
- ✅ Lee, escribe y busca archivos en sandbox aislado
- ✅ Verifica compilación automáticamente
- ✅ Compresión de contexto para conversaciones largas
- ✅ Corrección iterativa de errores

## Setup
1. `pip install -r requirements.txt`
2. Configurar credenciales en `.env` o Colab Secrets
3. Ejecutar `main.py`

## Uso
\```python
historial, resp = run_agent(bedrock, "Crea un todo app", sbx=sbx)
\```
```

---

## 📅 Cronograma Estimado

| Fase | Descripción                       | Tiempo    | Dependencias |
| ---- | --------------------------------- | --------- | ------------ |
| 0    | Setup e infraestructura           | 30-45 min | —            |
| 1    | Herramientas filesystem           | 2-3 h     | Fase 0       |
| 2    | Compresión de contexto            | 1.5-2 h   | Fase 0       |
| 3    | System prompt                     | 1 h       | —            |
| 4    | Loop del agente + pruebas         | 2-3 h     | Fases 1,2,3  |
| 5    | Interfaz Gradio (opcional)        | 1-2 h     | Fase 4       |
| 6    | Testing y documentación           | 1-2 h     | Fase 4       |
|      | **TOTAL**                         | **9-14 h** |             |

---

## 📦 Entregables Finales

| #   | Entregable                                                    | Estado |
| --- | ------------------------------------------------------------- | ------ |
| 1   | Repositorio con código completo y estructura organizada       | ⬜     |
| 2   | `lib/sbx_tools.py` con todas las herramientas                | ⬜     |
| 3   | `lib/context_manager.py` con compresión funcional            | ⬜     |
| 4   | `lib/prompts.py` con system prompt optimizado                | ⬜     |
| 5   | `lib/agent.py` con loop completo + compresión                | ⬜     |
| 6   | Prueba 1: App generada desde cero (+ captura)                | ⬜     |
| 7   | Prueba 2: Corrección sobre misma conversación (+ captura)    | ⬜     |
| 8   | `screenshots/app_before.png`                                 | ⬜     |
| 9   | `screenshots/app_after.png`                                  | ⬜     |
| 10  | `README.md` documentando el proyecto                         | ⬜     |
| 11  | Tests unitarios (al menos para herramientas)                 | ⬜     |

---

## ⚠️ Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigación |
| ------ | ------- | ---------- |
| E2B no tiene Node.js | Alto | Verificar con `node --version` al inicio; usar imagen custom si falta |
| Nova Pro no sigue instrucciones de tool use | Alto | Probar con prompt más explícito; fallback a Claude via Bedrock |
| Compilación Next.js falla por dependencias | Medio | Instalar deps antes de build; incluir en setup |
| Token limit alcanzado antes de comprimir | Medio | Reducir MAX_TOKENS; truncar tool results largos |
| `write_file` con contenido con caracteres especiales | Medio | Usar `sbx.files.write()` directo en vez de generar código |
| Sandbox timeout en builds largos | Bajo | Timeout de 2h; reiniciar si expira |

---

## 💡 Tips de Implementación

1. **Empezar por Fase 1** — sin herramientas robustas, nada funciona
2. **Testear cada herramienta individualmente** antes de integrar
3. **La compresión (Fase 2) es independiente** — puede desarrollarse en paralelo
4. **El system prompt se itera** — empezar simple, refinar según comportamiento
5. **Truncar tool results** — si `next build` devuelve 500 líneas,
   solo pasar las últimas 50 al LLM
6. **Guardar logs de cada sesión** — útil para debuggear el agente
7. **Si el modelo no usa herramientas**, verificar que los schemas se
   convierten correctamente a formato Bedrock

---