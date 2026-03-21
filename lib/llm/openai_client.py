"""
Proveedor OpenAI para Strands.
Requiere: pip install 'strands-agents[openai]' y OPENAI_API_KEY.
"""
import os
from lib.config.schema import ModelConfig


def build(m: ModelConfig):
    """Construye un OpenAIModel con los parámetros de configuración.

    Args:
        m: Configuración del modelo leída desde settings.yaml.

    Returns:
        Instancia de OpenAIModel lista para usar con Strands Agent.

    Raises:
        ImportError: Si strands-agents[openai] no está instalado.
    """
    try:
        from strands.models.openai import OpenAIModel
    except ImportError:
        raise ImportError("Instala el proveedor OpenAI: pip install 'strands-agents[openai]'")

    return OpenAIModel(
        client_args={"api_key": os.environ["OPENAI_API_KEY"]},
        model_id=m.model_id,
        params={"temperature": m.temperature, "max_tokens": m.max_tokens},
    )
