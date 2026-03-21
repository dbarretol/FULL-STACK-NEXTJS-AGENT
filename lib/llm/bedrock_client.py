"""
Proveedor AWS Bedrock para Strands.
Requiere: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION (o configurados via aws configure).
"""
from lib.config.schema import ModelConfig


def build(m: ModelConfig):
    """Construye un BedrockModel con los parámetros de configuración.

    Args:
        m: Configuración del modelo leída desde settings.yaml.

    Returns:
        Instancia de BedrockModel lista para usar con Strands Agent.
    """
    from strands.models.bedrock import BedrockModel

    return BedrockModel(
        model_id=m.model_id,
        region_name=m.region_name,
        temperature=m.temperature,
        max_tokens=m.max_tokens,
        streaming=m.streaming,
    )
