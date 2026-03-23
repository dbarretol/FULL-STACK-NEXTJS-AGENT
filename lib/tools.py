"""
Herramientas del agente usando el decorador @tool de Strands.
El sandbox E2B se accede como global de módulo, inicializado en main.py.
Los límites y constantes se leen desde lib.config.cfg.
"""
import json
import logging
import time
import urllib.request
import urllib.error
from e2b_code_interpreter import Sandbox
from strands import tool
from lib.config import cfg

logger = logging.getLogger("agent.tools")

# Global: inicializado en main.py antes de crear el agente
sbx: Sandbox | None = None


class ToolError(Exception):
    """Error controlado de herramienta. El mensaje se envía al LLM para que reintente."""
    pass


def _run(code: str) -> dict:
    """Ejecuta código Python en el sandbox y retorna stdout/stderr/error."""
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
    logger.debug("execute_code | code=%s", code[:120].replace("\n", "↵"))
    result = _run(code)
    if not result["success"]:
        logger.warning("execute_code FAILED | error=%s", result["error"])
    else:
        logger.debug("execute_code OK | stdout_lines=%d", len(result["stdout"]))
    return result


@tool
def list_directory(path: str = ".") -> dict:
    """List files and folders in a sandbox directory.

    Args:
        path: Directory path to list. Defaults to current directory.

    Returns:
        Dict with entries (list of {name, type, size}) and count.
    """
    logger.debug("list_directory | path=%s", path)
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
        logger.warning("list_directory FAILED | path=%s error=%s", path, result["error"])
        return {"error": f"Error listando {path}: {result['error']}"}
    try:
        parsed = json.loads("".join(result["stdout"]))
        logger.debug("list_directory OK | path=%s count=%s", path, parsed.get("count"))
        return parsed
    except json.JSONDecodeError:
        logger.error("list_directory JSON parse error | stdout=%s", result["stdout"])
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
    logger.debug("read_file | path=%s offset=%d", path, offset)
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
        logger.warning("read_file FAILED | path=%s error=%s", path, result["error"])
        return {"error": f"Error leyendo {path}: {result['error']}"}
    try:
        parsed = json.loads("".join(result["stdout"]))
        if "error" in parsed:
            logger.warning("read_file NOT FOUND | path=%s", path)
        else:
            logger.debug("read_file OK | path=%s size=%d truncated=%s", path, parsed.get("size", 0), parsed.get("truncated"))
        return parsed
    except json.JSONDecodeError:
        logger.error("read_file JSON parse error | path=%s", path)
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
    logger.info("write_file | path=%s bytes=%d", path, len(content.encode("utf-8")))
    max_write = cfg.tools.max_write_chars
    if len(content) > max_write:
        logger.warning("write_file REJECTED | path=%s size=%d max=%d", path, len(content), max_write)
        return {"error": f"Contenido demasiado grande: {len(content)} chars (max {max_write})"}
    try:
        sbx.files.write(path, content)
        logger.info("write_file OK | path=%s", path)
        return {"message": f"Archivo '{path}' escrito correctamente", "bytes_written": len(content.encode("utf-8"))}
    except Exception as e:
        logger.error("write_file EXCEPTION | path=%s error=%s", path, e)
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
    logger.debug("search_file_content | pattern=%s path=%s", pattern, path)
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
        logger.warning("search_file_content FAILED | pattern=%s error=%s", pattern, result["error"])
        return {"error": f"Error buscando '{pattern}': {result['error']}"}
    try:
        parsed = json.loads("".join(result["stdout"]))
        logger.debug("search_file_content OK | pattern=%s total=%d", pattern, parsed.get("total", 0))
        return parsed
    except json.JSONDecodeError:
        logger.error("search_file_content JSON parse error")
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
    logger.info("replace_in_file | path=%s old_snippet=%s", path, old[:60].replace("\n", "↵"))
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
        logger.warning("replace_in_file read FAILED | path=%s", path)
        return {"error": f"Error leyendo {path}: {read_result['error']}"}
    try:
        file_data = json.loads("".join(read_result["stdout"]))
    except json.JSONDecodeError:
        logger.error("replace_in_file JSON parse error | path=%s", path)
        return {"error": "Output inesperado al leer archivo"}
    if "error" in file_data:
        return file_data

    content = file_data["content"]
    count = content.count(old)
    if count == 0:
        logger.warning("replace_in_file PATTERN NOT FOUND | path=%s snippet=%s", path, old[:60])
        return {"error": f"Patrón no encontrado en {path}: '{old[:80]}'"}
    try:
        sbx.files.write(path, content.replace(old, new))
        logger.info("replace_in_file OK | path=%s replacements=%d", path, count)
    except Exception as e:
        logger.error("replace_in_file write EXCEPTION | path=%s error=%s", path, e)
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
    logger.debug("glob_files | pattern=%s", pattern)
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
        logger.warning("glob_files FAILED | pattern=%s error=%s", pattern, result["error"])
        return {"error": f"Error en glob '{pattern}': {result['error']}"}
    try:
        parsed = json.loads("".join(result["stdout"]))
        logger.debug("glob_files OK | pattern=%s total=%d", pattern, parsed.get("total", 0))
        return parsed
    except json.JSONDecodeError:
        logger.error("glob_files JSON parse error | pattern=%s", pattern)
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
    logger.info("run_command | cmd=%s workdir=%s timeout=%d", command, workdir, timeout)
    t0 = time.monotonic()
    try:
        result = sbx.commands.run(command, cwd=workdir, timeout=timeout)
        elapsed = time.monotonic() - t0
        if result.exit_code != 0:
            logger.warning(
                "run_command FAILED | cmd=%s exit=%d elapsed=%.1fs\nSTDERR: %s",
                command, result.exit_code, elapsed,
                (result.stderr or "")[-800:],
            )
        else:
            logger.info("run_command OK | cmd=%s exit=0 elapsed=%.1fs", command, elapsed)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "success": result.exit_code == 0,
        }
    except Exception as e:
        logger.error("run_command EXCEPTION | cmd=%s error=%s", command, e)
        return {"error": str(e), "success": False}


@tool
def start_dev_server(command: str = "npm run dev", workdir: str = "/home/user/app", port: int = 3000) -> dict:
    """Start a long-running dev server in the background, wait until it is ready, and return its public URL.

    If the server is already running on the given port, returns the existing URL immediately without
    relaunching. Use this only once per session — Next.js hot reload handles file changes automatically.

    Args:
        command: Command to start the server. Defaults to 'npm run dev'.
        workdir: Directory where the command runs. Defaults to /home/user/app.
        port: Port the server listens on. Defaults to 3000.

    Returns:
        Dict with url (public preview URL), ready (bool), and success flag.
    """
    host = sbx.get_host(port)
    url = f"https://{host}"
    logger.info("start_dev_server | cmd=%s workdir=%s port=%d url=%s", command, workdir, port, url)

    def _is_ready() -> bool:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                return resp.status < 500
        except urllib.error.HTTPError as e:
            return e.code < 500
        except Exception:
            return False

    def _page_compiled() -> bool:
        """Verifica que la página principal ya compiló leyendo el HTML de respuesta."""
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                if resp.status >= 500:
                    return False
                html = resp.read(4096).decode("utf-8", errors="ignore")
                # Next.js App Router no usa __NEXT_DATA__, usa streaming de cuerpo.
                # Buscamos etiquetas básicas que indiquen que el HTML no es un error de E2B.
                return any(m in html for m in ["<main", "<div", "<body", "<h1", "Next.js"])
        except urllib.error.HTTPError as e:
            return e.code < 500
        except Exception:
            return False

    # Si ya está corriendo, matamos para asegurar que tome el último build (.next)
    if _is_ready():
        logger.info("start_dev_server | already running, restarting to ensure latest build | url=%s", url)
        # Matamos procesos previos de node para liberar el puerto 3000
        _run("pkill -9 -f node || true")
        time.sleep(2)

    # Detección automática de build: si existe .next, preferimos 'npm run start' (más estable/rápido)
    check_build = _run(f"import os; print(os.path.isdir('{workdir}/.next'))")
    has_build = "True" in "".join(check_build["stdout"])
    
    if command == "npm run dev" and has_build:
        command = "npm run start"
        logger.info("start_dev_server | build detected, switching to production mode: %s", command)

    # Forzar binding a 0.0.0.0 para Next.js si es el comando por defecto
    if command in ["npm run dev", "npm run start"]:
        command = f"{command} -- -H 0.0.0.0"

    try:
        if not _is_ready():
            logger.info("start_dev_server LAUNCHING | cmd=%s", command)
            sbx.commands.run(command, cwd=workdir, background=True)

        # Fase 1: espera a que el servidor levante
        deadline = time.monotonic() + 120
        attempt = 0
        while time.monotonic() < deadline:
            attempt += 1
            if _is_ready():
                logger.info("start_dev_server SERVER UP | url=%s attempts=%d", url, attempt)
                break
            logger.debug("start_dev_server polling server | attempt=%d", attempt)
            time.sleep(3)
        else:
            logger.error("start_dev_server TIMEOUT waiting for server | url=%s", url)
            return {"url": url, "ready": False, "success": False,
                    "error": "El servidor no levantó en 120 segundos."}

        # Fase 2: espera a que la página principal compile (Next.js compila on-demand en dev)
        # En producción (npm run start) es instantáneo, pero igual verificamos.
        logger.info("start_dev_server waiting for page compile/hydration | url=%s", url)
        compile_deadline = time.monotonic() + 60
        compile_attempt = 0
        while time.monotonic() < compile_deadline:
            compile_attempt += 1
            if _page_compiled():
                elapsed = 120 - (deadline - time.monotonic())
                logger.info("start_dev_server PAGE READY | url=%s compile_attempts=%d",
                            url, compile_attempt)
                return {"url": url, "ready": True, "success": True,
                        "message": f"Servidor listo en {url}"}
            logger.debug("start_dev_server waiting compile | attempt=%d", compile_attempt)
            time.sleep(3)

        # Si no detectamos markers pero el servidor responde, devolvemos success
        logger.warning("start_dev_server compile check inconclusive, but server is up | url=%s", url)
        return {"url": url, "ready": True, "success": True,
                "message": f"Servidor listo en {url} (verificación de hidratación pendiente)"}

    except Exception as e:
        logger.error("start_dev_server EXCEPTION | error=%s", e)
        return {"error": str(e), "success": False}


@tool
def validate_app() -> dict:
    """Valida la app Next.js ejecutando checks de calidad: TypeScript, build y linter.

    Ejecuta secuencialmente:
    1. npx tsc --noEmit (verifica tipos)
    2. npm run build (verifica que compila)
    3. npm run lint (verifica estilo)

    Si alguno falla, devuelve los errores completos para que el agente los corrija.

    Returns:
        Dict con success (bool), errors (list), y message descriptivo.
    """
    logger.info("validate_app | starting validation checks")

    # Check 1: TypeScript
    result = sbx.commands.run("npx tsc --noEmit", cwd="/home/user/app", timeout=60)
    if result.exit_code != 0:
        logger.warning("validate_app FAILED | tsc errors\n%s", result.stderr or result.stdout)
        return {
            "success": False,
            "errors": ["TypeScript errors", result.stderr or result.stdout],
            "message": f"Errores de TypeScript detectados:\n{result.stderr or result.stdout}",
        }
    logger.info("validate_app OK | tsc passed")

    # Check 2: Build
    result = sbx.commands.run("npm run build", cwd="/home/user/app", timeout=120)
    if result.exit_code != 0:
        logger.warning("validate_app FAILED | build errors\n%s", result.stderr or result.stdout)
        return {
            "success": False,
            "errors": ["Build failed", result.stderr or result.stdout],
            "message": f"Error en el build:\n{result.stderr or result.stdout}",
        }
    logger.info("validate_app OK | build passed")

    # Check 3: Lint (opcional, pero recomendado)
    result = sbx.commands.run("npm run lint", cwd="/home/user/app", timeout=60)
    if result.exit_code != 0:
        logger.warning("validate_app WARNING | lint issues\n%s", result.stderr or result.stdout)
        return {
            "success": True,
            "errors": ["Lint warnings", result.stderr or result.stdout],
            "message": f"Advertencias de lint detectadas (la app funciona):\n{result.stderr or result.stdout}",
        }

    logger.info("validate_app SUCCESS | all checks passed")
    return {
        "success": True,
        "errors": [],
        "message": "Validación completada: TypeScript OK, Build OK, Lint OK.\n"
                   "IMPORTANTE: Como estás en modo PRODUCCION (npm run start), debes llamar a "
                   "start_dev_server de nuevo para que el usuario pueda ver estos cambios.",
    }
