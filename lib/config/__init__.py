"""
Módulo config — re-exporta cfg (singleton Settings) y los tipos del schema.
Uso: from lib.config import cfg
"""
from lib.config.schema import (
    Settings, ModelConfig, AgentConfig,
    ContextConfig, SandboxConfig, ToolsConfig, GradioConfig,
)
from lib.config.loader import load_settings

# Singleton cargado una sola vez al importar el módulo
cfg: Settings = load_settings()

__all__ = [
    "cfg",
    "Settings", "ModelConfig", "AgentConfig",
    "ContextConfig", "SandboxConfig", "ToolsConfig", "GradioConfig",
]
