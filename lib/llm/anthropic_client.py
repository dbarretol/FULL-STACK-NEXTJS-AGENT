"""
Proveedor Anthropic (directo) para Strands.
Requiere: pip install 'strands-agents[anthropic]' y ANTHROPIC_API_KEY.
"""
import os
from lib.config.schema import ModelConfig


def build(m: ModelConfig):
    """Construye un AnthropicModel con los parámetros de configuración.

    Args:
        m: Configuración del modelo leída desde settings.yaml.

    Returns:
        Instancia de AnthropicModel lista para usar con Strands Agent.

    Raises:
        ImportError: Si strands-agents[anthropic] no está instalado.
    """
    try:
        from strands.models.anthropic import AnthropicModel
    except ImportError:
        raise ImportError("Instala el proveedor Anthropic: pip install 'strands-agents[anthropic]'")

    return AnthropicModel(
        client_args={"api_key": os.environ["ANTHROPIC_API_KEY"]},
        model_id=m.model_id,
        max_tokens=m.max_tokens,
        params={"temperature": m.temperature},
    )
