# ♊ Guía de Gemini en Strands Agents

Esta guía detalla cómo configurar y utilizar el proveedor de **Google Gemini** dentro del proyecto del agente full-stack, aprovechando el SDK de **Strands Agents**.

---

## 🚀 1. Instalación y Configuración

Para utilizar Gemini, debes instalar el grupo de dependencias opcional correspondiente.

### Instalación de dependencias

Utiliza `uv` (recomendado) para instalar el soporte de Gemini:

```bash
uv add .[gemini]
```

O usando `pip` tradicional:

```bash
pip install 'strands-agents[gemini]' strands-agents-tools
```

---

### Configuración de Variables de Entorno

Obtén tu API Key desde [Google AI Studio](https://aistudio.google.com/) y configúrala en tu archivo `.env` o en tu terminal:

```bash
# Archivo .env
GOOGLE_API_KEY=tu_api_key_aqui
```

---

## 🛠️ 2. Ejemplo Mínimo de Uso (SDK)

Si deseas probar el modelo de forma aislada antes de integrarlo al flujo full-stack:

```python
import os
from strands import Agent
from strands.models.gemini import GeminiModel

# Asegúrate de tener GOOGLE_API_KEY en el entorno
model = GeminiModel(
    client_args={"api_key": os.environ["GOOGLE_API_KEY"]},
    model_id="gemini-2.5-flash",
    params={"temperature": 0.7}
)

agent = Agent(model=model)
response = agent("Explica brevemente qué es un React Server Component.")
print(response)
```

---

## 🏗️ 3. Pruebas del Agente Full-Stack con Gemini

Para que el proyecto completo utilice Gemini como cerebro principal, sigue estos pasos:

### Paso 1: Cambiar el proveedor en la configuración

Edita el archivo `lib/config/settings.yaml` y establece `gemini` como el proveedor activo:

```yaml
# lib/config/settings.yaml
llm_provider: "gemini"

models:
  gemini:
    model_id: "gemini-2.5-flash"
    temperature: 0.2
```

### Paso 2: Verificar dependencias

Asegúrate de haber instalado el grupo `[gemini]` (ver sección 1).

### Paso 3: Ejecución y Validación

Lanza el agente desde la CLI o la interfaz Gradio:

```bash
uv run python main.py
# O
uv run python -m ui.gradio_app
```

**Qué verificar:**

* **Logs de inicio**: Deberías ver el mensaje de inicialización indicando el uso de Gemini.
* **Herramientas**: Verifica que el agente llame a `list_directory` o `write_file` correctamente.
* **Compresión**: Si la conversación es larga, `lib/context_manager.py` utilizará Gemini para generar los resúmenes de contexto.

---

## ⚙️ 4. Parámetros Clave de Configuración

Al configurar el `GeminiModel` en `settings.yaml`, puedes ajustar:

| Parámetro           | Recomendado (Test) | Recomendado (Prod) | Descripción                                         |
| :------------------ | :----------------- | :----------------- | :-------------------------------------------------- |
| `temperature`       | 0.7                | 0.2                | Controla la creatividad. Bajo es mejor para código. |
| `max_output_tokens` | 2048               | 4096               | Límite de la respuesta del modelo.                  |
| `top_p`             | 0.95               | 0.9                | Selección de tokens basada en probabilidad.         |

---

## ❓ 5. Solución de Problemas (Troubleshooting)

### Error: `ModuleNotFoundError: No module named 'google.genai'`

**Causa:** Confusión entre SDKs o dependencias incompletas.
**Solución:**

* Ejecuta:

  ```bash
  uv add .[gemini]
  ```
* Si estás trabajando fuera de Strands y usando el SDK moderno:

  ```bash
  uv add google-genai
  ```

---

### Error: API Key inválida

**Síntoma:** Errores 401 o "Unauthorized".
**Solución:** Verifica que `GOOGLE_API_KEY` esté correctamente cargada en `os.environ`. En Windows PowerShell usa:

```bash
$env:GOOGLE_API_KEY="tu_llave"
```

---

### Error: `ModelThrottledException` (Rate Limiting)

**Síntoma:** El modelo responde con errores de cuota superada.
**Solución:**

* Reduce la frecuencia de las peticiones si usas el plan gratuito.
* Aumenta el `timeout` en la configuración para tareas pesadas.

---

## 🌟 6. Características Avanzadas (Opcional)

* **Structured Output**: El SDK integra automáticamente modelos de **Pydantic** para forzar respuestas en JSON válido.
* **Multimodalidad**: Puedes pasar imágenes o documentos (PDF) al agente simplemente añadiendo la ruta del archivo en el contenido del mensaje.

---