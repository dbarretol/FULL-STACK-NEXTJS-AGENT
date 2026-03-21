"""
Factory de modelos LLM.
Selecciona el cliente correcto según lib.config.cfg.llm_provider.
Para agregar un nuevo proveedor: crear su _client.py y añadir una entrada al mapa.
"""
from lib.config import cfg

_PROVIDERS: dict[str, str] = {
    "bedrock":   "lib.llm.bedrock_client",
    "anthropic": "lib.llm.anthropic_client",
    "openai":    "lib.llm.openai_client",
    "gemini":    "lib.llm.gemini_client",
    "llamaapi":  "lib.llm.llamaapi_client",
}


def build_model():
    """Construye y retorna la instancia del modelo LLM configurado en settings.yaml.

    Importa dinámicamente el módulo del proveedor activo para evitar
    cargar dependencias opcionales que no estén instaladas.

    Returns:
        Instancia del modelo compatible con Strands Agent.

    Raises:
        ValueError: Si llm_provider no está en la lista de proveedores soportados.
        ImportError: Si el paquete extra del proveedor no está instalado.
    """
    provider = cfg.llm_provider

    if provider not in _PROVIDERS:
        raise ValueError(
            f"Proveedor LLM no soportado: '{provider}'. "
            f"Valores válidos: {', '.join(_PROVIDERS)}"
        )

    import importlib
    module = importlib.import_module(_PROVIDERS[provider])
    return module.build(cfg.model)
