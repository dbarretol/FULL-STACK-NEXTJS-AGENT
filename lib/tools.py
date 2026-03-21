"""
Herramientas del agente usando el decorador @tool de Strands.
El sandbox E2B se accede como global de módulo, inicializado en main.py.
"""
import json
from e2b_code_interpreter import Sandbox
from strands import tool

# Global: inicializado en main.py antes de crear el agente
sbx: Sandbox | None = None


class ToolError(Exception):
    """Error controlado de herramienta. El mensaje se envía al LLM para que reintente."""
    pass


def _run(code: str) -> dict:
    """Ejecuta código en el sandbox y retorna stdout/stderr/error."""
    execution = sbx.run_code(code)
    stdout = list(execution.logs.stdout) if execution.logs.stdout else []
    stderr = list(execution.logs.stderr) if execution.logs.stderr else []
    error = f"{execution.error.name}: {execution.error.value}" if execution.error else None
    results = [r.text for r in execution.results if hasattr(r, "text") and r.text]
    return {"stdout": stdout, "stderr": stderr, "results": results, "error": error, "success": error is None}


@tool
def execute_code(code: str) -> dict:
    """Execute Python code or shell commands in the E2B sandbox.

    Use this to: install npm packages, run Next.js builds, execute shell commands
    (wrap shell with subprocess), verify compilation with `npx tsc --noEmit`.

    Args:
        code: Python code to execute. For shell commands use subprocess.run().

    Returns:
        Dict with stdout, stderr, results, error, and success flag.
    """
    result = _run(code)
    return result


@tool
def list_directory(path: str = ".") -> dict:
    """List files and folders in a sandbox directory.

    Args:
        path: Directory path to list. Defaults to current directory.

    Returns:
        Dict with entries (list of {name, type, size}) and count.
    """
    code = f"""
import os, json
path = {repr(path)}
if not os.path.isdir(path):
    print(json.dumps({{"error": f"Directorio '{{path}}' no existe"}}))
else:
    entries = []
    for name in sorted(os.listdir(path)):
        full = os.path.join(path, name)
        entries.append({{
            "name": name,
            "type": "dir" if os.path.isdir(full) else "file",
            "size": os.path.getsize(full) if os.path.isfile(full) else None
        }})
    print(json.dumps({{"entries": entries, "count": len(entries)}}))
"""
    result = _run(code)
    if not result["success"]:
        return {"error": f"Error listando {path}: {result['error']}"}
    try:
        return json.loads("".join(result["stdout"]))
    except json.JSONDecodeError:
        return {"error": f"Output inesperado: {''.join(result['stdout'])}"}


@tool
def read_file(path: str, limit: int = 50000, offset: int = 0) -> dict:
    """Read the content of a file from the sandbox.

    Args:
        path: File path to read.
        limit: Maximum characters to read. Defaults to 50000.
        offset: Starting byte position. Defaults to 0.

    Returns:
        Dict with content, size, and truncated flag.
    """
    code = f"""
import os, json
path = {repr(path)}
if not os.path.isfile(path):
    print(json.dumps({{"error": f"Archivo '{{path}}' no existe"}}))
else:
    size = os.path.getsize(path)
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        f.seek({offset})
        content = f.read({limit})
    truncated = ({offset} + len(content)) < size
    print(json.dumps({{"content": content, "size": size, "truncated": truncated}}))
"""
    result = _run(code)
    if not result["success"]:
        return {"error": f"Error leyendo {path}: {result['error']}"}
    try:
        return json.loads("".join(result["stdout"]))
    except json.JSONDecodeError:
        return {"error": f"Output inesperado: {''.join(result['stdout'])}"}


@tool
def write_file(path: str, content: str) -> dict:
    """Write content to a file in the sandbox. Creates parent directories automatically.

    Args:
        path: Destination file path.
        content: Full file content to write.

    Returns:
        Dict with message and bytes_written.
    """
    MAX_WRITE = 1_000_000
    if len(content) > MAX_WRITE:
        return {"error": f"Contenido demasiado grande: {len(content)} chars (max {MAX_WRITE})"}
    try:
        sbx.files.write(path, content)
        return {"message": f"Archivo '{path}' escrito correctamente", "bytes_written": len(content.encode("utf-8"))}
    except Exception as e:
        return {"error": f"Error escribiendo {path}: {str(e)}"}


@tool
def search_file_content(pattern: str, path: str = ".", max_results: int = 20) -> dict:
    """Search for a text pattern across all project files in the sandbox.

    Skips node_modules, .next, .git, and __pycache__ directories.

    Args:
        pattern: Text pattern to search for (case-insensitive).
        path: Root directory to search from. Defaults to current directory.
        max_results: Maximum number of matches to return. Defaults to 20.

    Returns:
        Dict with matches (list of {file, line, content}), total count, and truncated flag.
    """
    code = f"""
import os, json
pattern = {repr(pattern)}
root = {repr(path)}
max_results = {max_results}
matches = []
total = 0
SKIP = {{'node_modules', '.next', '.git', '__pycache__'}}
EXTS = {{'.js','.jsx','.ts','.tsx','.css','.html','.json','.md','.py','.txt','.env'}}

for dirpath, dirs, filenames in os.walk(root):
    dirs[:] = [d for d in dirs if d not in SKIP]
    for fname in filenames:
        if not any(fname.endswith(e) for e in EXTS):
            continue
        fpath = os.path.join(dirpath, fname)
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    if pattern.lower() in line.lower():
                        total += 1
                        if len(matches) < max_results:
                            matches.append({{"file": fpath, "line": i, "content": line.strip()[:200]}})
        except:
            pass

print(json.dumps({{"matches": matches, "total": total, "truncated": total > max_results}}))
"""
    result = _run(code)
    if not result["success"]:
        return {"error": f"Error buscando '{pattern}': {result['error']}"}
    try:
        return json.loads("".join(result["stdout"]))
    except json.JSONDecodeError:
        return {"error": "Output inesperado del sandbox"}


@tool
def replace_in_file(path: str, old: str, new: str) -> dict:
    """Replace all occurrences of a text string in a sandbox file.

    Args:
        path: File path to modify.
        old: Exact text to find and replace.
        new: Replacement text.

    Returns:
        Dict with replacements count and message.
    """
    # Leer el archivo directamente (sin pasar por el decorador @tool)
    read_result = _run(f"""
import os, json
path = {repr(path)}
if not os.path.isfile(path):
    print(json.dumps({{"error": f"Archivo '{{path}}' no existe"}}))
else:
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    print(json.dumps({{"content": content}}))
""")
    if not read_result["success"]:
        return {"error": f"Error leyendo {path}: {read_result['error']}"}
    try:
        file_data = json.loads("".join(read_result["stdout"]))
    except json.JSONDecodeError:
        return {"error": "Output inesperado al leer archivo"}
    if "error" in file_data:
        return file_data

    content = file_data["content"]
    count = content.count(old)
    if count == 0:
        return {"error": f"Patrón no encontrado en {path}: '{old[:80]}'"}

    try:
        sbx.files.write(path, content.replace(old, new))
    except Exception as e:
        return {"error": f"Error escribiendo {path}: {str(e)}"}

    return {"replacements": count, "message": f"{count} reemplazo(s) en {path}"}


@tool
def glob_files(pattern: str) -> dict:
    """Find files by name or extension pattern using glob in the sandbox.

    Args:
        pattern: Glob pattern, e.g. '**/*.tsx' or 'app/**/*.css'.

    Returns:
        Dict with files list and total count.
    """
    code = f"""
import glob, json
files = glob.glob({repr(pattern)}, recursive=True)
files = [f for f in files if 'node_modules' not in f and '.next' not in f]
print(json.dumps({{"files": files[:100], "total": len(files)}}))
"""
    result = _run(code)
    if not result["success"]:
        return {"error": f"Error en glob '{pattern}': {result['error']}"}
    try:
        return json.loads("".join(result["stdout"]))
    except json.JSONDecodeError:
        return {"error": "Output inesperado del sandbox"}
