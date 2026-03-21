# 🧠 Tarea Final: Agente de Código Full Stack

## 🎯 Objetivo

Construir un agente que:

* Reciba instrucciones en lenguaje natural
* Genere una aplicación web completa
* Lea y escriba archivos
* Verifique que el código compile correctamente

⚠️ El reto no es solo que funcione, sino que pueda mantener rendimiento en **conversaciones largas sin quedarse sin memoria**.

---

## ⚠️ Problema clave: el contexto

Cada acción del agente consume tokens.
En tareas complejas, el consumo puede superar fácilmente los **40,000 tokens**.

### 💡 Solución: Runtime Summary

1. Definir un límite de tokens (ej. `40,000`)
2. Al alcanzarlo:

   * Tomar el **70% de los mensajes más antiguos**
   * Resumirlos usando un LLM
   * Reemplazarlos por ese resumen
3. Continuar la conversación con el contexto reducido

---

## 🛠️ Parte 1 — Herramientas del sistema de archivos

Implementar en: `lib/sbx_tools.py`

Incluye una excepción personalizada: `ToolError` para manejar errores.

### Funciones requeridas

| Función                                     | Descripción                                             |
| ------------------------------------------- | ------------------------------------------------------- |
| `list_directory(path)`                      | Lista archivos y carpetas                               |
| `read_file(path)`                           | Lee el contenido de un archivo                          |
| `write_file(path, content)`                 | Escribe contenido en un archivo                         |
| `search_file_content(pattern, max_results)` | Busca un patrón y devuelve resultados paginados en JSON |

### Funciones opcionales

| Función                           | Descripción                           |
| --------------------------------- | ------------------------------------- |
| `replace_in_file(path, old, new)` | Reemplaza texto dentro de un archivo  |
| `glob(pattern)`                   | Busca archivos por nombre o extensión |

---

## 🧩 Parte 2 — Compresión de contexto

Cuando la conversación crece demasiado, se debe comprimir el historial.

### Estrategia

* Comprimir el **70% de los mensajes más antiguos**
* Mantener intactos los mensajes recientes
* Reemplazar los antiguos por un resumen

### Código base

```python
MAX_TOKENS = 40_000
COMPRESSION_RATIO = 0.70

def count_tokens(messages: list) -> int:
    pass

def compress_context(messages: list, llm_client) -> list:
    """
    - Comprime el 70% más antiguo
    - Retorna:
      [resumen_user, resumen_assistant] + mensajes_recientes
    """
    pass

def maybe_compress(messages: list, llm_client) -> list:
    """
    - Solo comprime si se supera el límite de tokens
    """
    pass
```

---

## 🧠 Parte 3 — System Prompt

Crear `SYSTEM_PROMPT_WEB_DEV` que defina:

* Cómo debe razonar el agente
* Qué stack usar (**Next.js**)
* Cuándo usar cada herramienta
* Cómo verificar que el código no rompa la app

---

## 🧪 Parte 4 — Prueba del agente

```python
historial = []

# Tarea 1
run_agent(
    "Crea una app de lista de tareas estilo Windows 95.",
    messages=historial
)

# Tarea 2 (usando el mismo historial)
run_agent(
    "Los íconos del nav son blancos y no se ven. Arréglalo.",
    messages=historial
)
```

---

## 📦 Entregables

* Repositorio con el código completo
* Capturas de la app:

  * Antes del ajuste
  * Después del ajuste

---