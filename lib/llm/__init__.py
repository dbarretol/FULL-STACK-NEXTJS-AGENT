"""
Módulo de inicialización del LLM.
Expone build_model() que devuelve el modelo correcto según lib.config.cfg.llm_provider.
Para cambiar de proveedor basta con editar llm_provider en settings.yaml.
"""
import os
from lib.config import cfg, ModelConfig


def build_model():
    """Construye y retorna la instancia del modelo LLM configurado.

    Lee lib.config.cfg para determinar el proveedor y los parámetros.
    Soporta: bedrock, anthropic, openai, gemini, llamaapi.

    Returns:
        Instancia del modelo compatible con Strands Agent.

    Raises:
        ValueError: Si el proveedor configurado no está soportado.
        ImportError: Si el paquete del proveedor no está instalado.
    """
    provider = cfg.llm_provider
    m: ModelConfig = cfg.model

    if provider == "bedrock":
        return _build_bedrock(m)
    elif provider == "anthropic":
        return _build_anthropic(m)
    elif provider == "openai":
        return _build_openai(m)
    elif provider == "gemini":
        return _build_gemini(m)
    elif provider == "llamaapi":
        return _build_llamaapi(m)
    else:
        raise ValueError(
            f"Proveedor LLM no soportado: '{provider}'. "
            "Valores válidos: bedrock, anthropic, openai, gemini, llamaapi"
        )


# ---------------------------------------------------------------------------
# Constructores por proveedor
# ---------------------------------------------------------------------------

def _build_bedrock(m: ModelConfig):
    from strands.models.bedrock import BedrockModel
    return BedrockModel(
        model_id=m.model_id,
        region_name=m.region_name,
        temperature=m.temperature,
        max_tokens=m.max_tokens,
        streaming=m.streaming,
    )


def _build_anthropic(m: ModelConfig):
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


def _build_openai(m: ModelConfig):
    try:
        from strands.models.openai import OpenAIModel
    except ImportError:
        raise ImportError("Instala el proveedor OpenAI: pip install 'strands-agents[openai]'")
    return OpenAIModel(
        client_args={"api_key": os.environ["OPENAI_API_KEY"]},
        model_id=m.model_id,
        params={"temperature": m.temperature, "max_tokens": m.max_tokens},
    )


def _build_gemini(m: ModelConfig):
    try:
        from strands.models.gemini import GeminiModel
    except ImportError:
        raise ImportError("Instala el proveedor Gemini: pip install 'strands-agents[gemini]'")
    return GeminiModel(
        client_args={"api_key": os.environ["GOOGLE_API_KEY"]},
        model_id=m.model_id,
        params={"temperature": m.temperature},
    )


def _build_llamaapi(m: ModelConfig):
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
