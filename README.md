# 🤖 Agente de Código Full Stack

Este proyecto es un agente de IA diseñado para generar aplicaciones web completas utilizando **Next.js**, **TypeScript** y **Tailwind CSS**. Implementa una estrategia de **Runtime Summary** para gestionar contextos largos de hasta 40,000 tokens mediante compresión automática del historial.

## 🚀 Requisitos Previos

1.  **Python 3.12+** (se recomienda usar `uv` para la gestión de dependencias).
2.  **E2B API Key**: Regístrate en [e2b.dev](https://e2b.dev/) para obtener una clave.
3.  **LLM Provider**: El agente soporta AWS Bedrock (por defecto), OpenAI, Anthropic, Gemini y LlamaAPI. Asegúrate de tener las credenciales correspondientes.

## 🛠️ Instalación y Configuración

### 1. Clonar el repositorio
```bash
git clone <url-del-repositorio>
cd AGENT-FULL-STACK
```

### 2. Instalar dependencias con `uv`
Si no tienes `uv` instalado, puedes obtenerlo desde [astral.sh/uv](https://astral.sh/uv).

```bash
uv sync
```
Esto creará un entorno virtual e instalará todas las dependencias definidas en `pyproject.toml`.

### 3. Configurar variables de entorno
Copia el archivo `.env.example` a `.env` y completa tus credenciales:

```bash
cp .env.example .env
```

Edita el archivo `.env`:
- `E2B_API_KEY`: Tu clave de E2B.
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`: Si usas AWS Bedrock (por defecto).

### 4. Ajustar configuración del agente (Opcional)
Puedes modificar el proveedor de LLM y los parámetros de compresión en `lib/config/settings.yaml`.

## 🧪 Cómo Probar el Proyecto

### Opción A: Ejecución desde CLI (Main)
El script principal ejecuta dos tareas de prueba: crear una app de tareas estilo Windows 95 y luego corregir un error visual.

```bash
uv run python main.py
```

### Opción B: Interfaz Gráfica (Gradio)
Para una experiencia interactiva, lanza la interfaz web:

```bash
uv run python -m ui.gradio_app
```
Una vez iniciada, abre la URL (usualmente `http://127.0.0.1:7860`) en tu navegador.

## 🧠 Verificación de Funcionalidades

Para confirmar que el agente cumple con los objetivos:

1.  **Generación de App**: Pide al agente crear un proyecto (ej: "Crea un dashboard de finanzas con Next.js").
2.  **Uso de Herramientas**: Observa en los logs cómo usa `list_directory`, `write_file` y `execute_code`.
3.  **Compresión de Contexto**: Si la conversación se alarga, verás logs indicando que el contexto ha superado los 40,000 tokens y se está comprimiendo un 70% del historial.
4.  **Verificación de Código**: El agente ejecutará automáticamente `npx tsc --noEmit` después de cambios importantes para asegurar que el código compila.

## 📂 Estructura del Proyecto

- `lib/tools.py`: Herramientas del sistema de archivos usando E2B.
- `lib/context_manager.py`: Lógica de compresión de contexto (Runtime Summary).
- `lib/prompts.py`: System prompt con el razonamiento del desarrollador senior.
- `ui/gradio_app.py`: Interfaz de usuario para pruebas interactivas.
- `main.py`: Orquestador principal y punto de entrada CLI.
