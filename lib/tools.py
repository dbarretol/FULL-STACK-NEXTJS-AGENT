"""
Herramientas del agente usando el decorador @tool de Strands.
El sandbox E2B se accede como global de módulo, inicializado en main.py.
Los límites y constantes se leen desde lib.config.cfg.
"""
import json
from e2b_code_interpreter import Sandbox
from strands import tool
from lib.config import cfg

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
    return _run(code)


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
def read_file(path: str, limit: int = 0, offset: int = 0) -> dict:
    """Read the content of a file from the sandbox.

    Args:
        path: File path to read.
        limit: Maximum characters to read. 0 means use the configured default.
        offset: Starting byte position. Defaults to 0.

    Returns:
        Dict with content, size, and truncated flag.
    """
    effective_limit = limit if limit > 0 else cfg.tools.max_read_chars
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
    max_write = cfg.tools.max_write_chars
    if len(content) > max_write:
        return {"error": f"Contenido demasiado grande: {len(content)} chars (max {max_write})"}
    try:
        sbx.files.write(path, content)
        return {"message": f"Archivo '{path}' escrito correctamente", "bytes_written": len(content.encode("utf-8"))}
    except Exception as e:
        return {"error": f"Error escribiendo {path}: {str(e)}"}


@tool
def search_file_content(pattern: str, path: str = ".", max_results: int = 0) -> dict:
    """Search for a text pattern across all project files in the sandbox.

    Skips node_modules, .next, .git, and __pycache__ directories.

    Args:
        pattern: Text pattern to search for (case-insensitive).
        path: Root directory to search from. Defaults to current directory.
        max_results: Maximum matches to return. 0 means use the configured default.

    Returns:
        Dict with matches (list of {file, line, content}), total count, and truncated flag.
    """
    effective_max = max_results if max_results > 0 else cfg.tools.search_max_results
    skip = set(cfg.tools.skip_dirs)
    exts = set(cfg.tools.searchable_extensions)

    code = f"""
import os, json
pattern = {repr(pattern)}
root = {repr(path)}
max_results = {effective_max}
matches = []
total = 0
SKIP = {repr(skip)}
EXTS = {repr(exts)}

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
    max_results = cfg.tools.glob_max_results
    skip = cfg.tools.skip_dirs
    code = f"""
import glob, json
files = glob.glob({repr(pattern)}, recursive=True)
skip = {repr(skip)}
files = [f for f in files if not any(s in f for s in skip)]
print(json.dumps({{"files": files[:{max_results}], "total": len(files)}}))
"""
    result = _run(code)
    if not result["success"]:
        return {"error": f"Error en glob '{pattern}': {result['error']}"}
    try:
        return json.loads("".join(result["stdout"]))
    except json.JSONDecodeError:
        return {"error": "Output inesperado del sandbox"}


@tool
def run_command(command: str, workdir: str = "/home/user", timeout: int = 60) -> dict:
    """Run a shell command in the sandbox and wait for it to finish.

    Use this for: npm install, npx create-next-app, npm run build, npx tsc, git init, etc.
    Do NOT use for long-running servers (use start_dev_server instead).

    Args:
        command: Shell command to execute, e.g. 'npm install' or 'npx tsc --noEmit'.
        workdir: Working directory for the command. Defaults to /home/user.
        timeout: Max seconds to wait. Defaults to 60.

    Returns:
        Dict with stdout, stderr, exit_code, and success flag.
    """
    try:
        result = sbx.commands.run(command, cwd=workdir, timeout=timeout)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "success": result.exit_code == 0,
        }
    except Exception as e:
        return {"error": str(e), "success": False}


@tool
def start_dev_server(command: str = "npm run dev", workdir: str = "/home/user/app", port: int = 3000) -> dict:
    """Start a long-running dev server in the background, wait until it is ready, and return its public URL.

    Launches the server, then polls the URL until it responds with HTTP 200 (or any non-connection-error
    response), confirming the app is live before returning. Times out after 120 seconds.

    Use this after the Next.js app is ready to preview it in the browser.

    Args:
        command: Command to start the server. Defaults to 'npm run dev'.
        workdir: Directory where the command runs. Defaults to /home/user/app.
        port: Port the server listens on. Defaults to 3000.

    Returns:
        Dict with url (public preview URL), ready (bool), and success flag.
    """
    import time
    import urllib.request
    import urllib.error

    try:
        sbx.commands.run(command, cwd=workdir, background=True)
        host = sbx.get_host(port)
        url = f"https://{host}"

        # Polling: espera hasta que el servidor responda
        deadline = time.time() + 120
        interval = 3
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=5) as resp:
                    if resp.status < 500:
                        return {"url": url, "ready": True, "success": True,
                                "message": f"Servidor listo en {url}"}
            except urllib.error.HTTPError as e:
                # 4xx significa que el servidor está vivo aunque devuelva error
                if e.code < 500:
                    return {"url": url, "ready": True, "success": True,
                            "message": f"Servidor listo en {url}"}
            except Exception:
                pass  # Conexión rechazada — servidor aún arrancando
            time.sleep(interval)

        return {"url": url, "ready": False, "success": False,
                "error": "El servidor no respondió en 120 segundos. Verifica que la app compile sin errores."}
    except Exception as e:
        return {"error": str(e), "success": False}
