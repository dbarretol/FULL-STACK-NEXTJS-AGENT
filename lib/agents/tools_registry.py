"""
Registro de subconjuntos de herramientas por rol de agente.
Cada agente recibe solo las herramientas que necesita para su especialidad.
"""
from lib.tools import (
    execute_code,
    list_directory,
    read_file,
    write_file,
    search_file_content,
    replace_in_file,
    glob_files,
    run_command,
    start_dev_server,
    validate_app,
)

# Herramientas de lectura/exploración (todos los agentes las necesitan)
_READ_TOOLS = [list_directory, read_file, search_file_content, glob_files]

# Herramientas de escritura de código
_WRITE_TOOLS = [write_file, replace_in_file]

# Herramientas de ejecución de comandos
_EXEC_TOOLS = [run_command, execute_code]

# Herramientas de servidor/validación
_SERVER_TOOLS = [start_dev_server, validate_app]

# ---------------------------------------------------------------------------
# Subconjuntos por rol
# ---------------------------------------------------------------------------

FRONTEND_TOOLS = _READ_TOOLS + _WRITE_TOOLS + _EXEC_TOOLS

BACKEND_TOOLS = _READ_TOOLS + _WRITE_TOOLS + _EXEC_TOOLS

UIUX_TOOLS = _READ_TOOLS + _WRITE_TOOLS + [run_command]

QA_TOOLS = _READ_TOOLS + _EXEC_TOOLS + _SERVER_TOOLS

# El agente de contexto solo necesita leer para poder resumir
CONTEXT_TOOLS = _READ_TOOLS
