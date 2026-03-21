"""
Proveedor Meta LlamaAPI para Strands.
Requiere: pip install 'strands-agents[llamaapi]' y LLAMA_API_KEY.
"""
import os
from lib.config.schema import ModelConfig


def build(m: ModelConfig):
    """Construye un LlamaAPIModel con los parámetros de configuración.

    Args:
        m: Configuración del modelo leída desde settings.yaml.

    Returns:
        Instancia de LlamaAPIModel lista para usar con Strands Agent.

    Raises:
        ImportError: Si strands-agents[llamaapi] no está instalado.
    """
    try:
        from strands.models.llamaapi import LlamaAPIModel
    except ImportError:
        raise ImportError("Instala el proveedor LlamaAPI: pip install 'strands-agents[llamaapi]'")

    return LlamaAPIModel(
        client_args={"api_key": os.environ["LLAMA_API_KEY"]},
        model_id=m.model_id,
        temperature=m.temperature,
        max_completion_tokens=m.max_completion_tokens,
    )
