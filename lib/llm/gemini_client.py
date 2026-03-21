"""
Proveedor Google Gemini para Strands.
Requiere: pip install 'strands-agents[gemini]' y GOOGLE_API_KEY.
"""
import os
from lib.config.schema import ModelConfig


def build(m: ModelConfig):
    """Construye un GeminiModel con los parámetros de configuración.

    Args:
        m: Configuración del modelo leída desde settings.yaml.

    Returns:
        Instancia de GeminiModel lista para usar con Strands Agent.

    Raises:
        ImportError: Si strands-agents[gemini] no está instalado.
    """
    try:
        from strands.models.gemini import GeminiModel
    except ImportError:
        raise ImportError("Instala el proveedor Gemini: pip install 'strands-agents[gemini]'")

    return GeminiModel(
        client_args={"api_key": os.environ["GOOGLE_API_KEY"]},
        model_id=m.model_id,
        params={"temperature": m.temperature},
    )
