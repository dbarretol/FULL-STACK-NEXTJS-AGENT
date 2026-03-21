"""
Carga settings.yaml y construye el objeto Settings tipado.
"""
import os
from pathlib import Path
import yaml

from lib.config.schema import (
    Settings, ModelConfig, AgentConfig,
    ContextConfig, SandboxConfig, ToolsConfig, GradioConfig,
)

_CONFIG_PATH = Path(__file__).parent / "settings.yaml"


def load_settings() -> Settings:
    """Lee settings.yaml y retorna un objeto Settings completamente tipado.

    La variable de entorno AWS_REGION sobreescribe region_name del YAML.

    Returns:
        Instancia de Settings con todos los valores cargados.
    """
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    provider = raw.get("llm_provider", "bedrock")
    model_raw = raw.get("models", {}).get(provider, {})
    region = os.getenv("AWS_REGION", model_raw.get("region_name", "us-east-1"))

    agent_raw = raw.get("agent", {})
    ctx_raw = raw.get("context", {})
    sbx_raw = raw.get("sandbox", {})
    tools_raw = raw.get("tools", {})
    gradio_raw = raw.get("gradio", {})

    return Settings(
        llm_provider=provider,
        model=ModelConfig(
            model_id=model_raw.get("model_id", "amazon.nova-pro-v1:0"),
            temperature=model_raw.get("temperature", 0.2),
            max_tokens=model_raw.get("max_tokens", 4096),
            region_name=region,
            streaming=model_raw.get("streaming", True),
            max_completion_tokens=model_raw.get("max_completion_tokens", 4096),
        ),
        agent=AgentConfig(
            max_handler_calls=agent_raw.get("max_handler_calls", 30),
        ),
        context=ContextConfig(
            max_tokens=ctx_raw.get("max_tokens", 40_000),
            compression_ratio=ctx_raw.get("compression_ratio", 0.70),
            chars_per_token=ctx_raw.get("chars_per_token", 4),
        ),
        sandbox=SandboxConfig(
            timeout_seconds=sbx_raw.get("timeout_seconds", 3600),
        ),
        tools=ToolsConfig(
            max_read_chars=tools_raw.get("max_read_chars", 50_000),
            max_write_chars=tools_raw.get("max_write_chars", 1_000_000),
            search_max_results=tools_raw.get("search_max_results", 20),
            glob_max_results=tools_raw.get("glob_max_results", 100),
            skip_dirs=tools_raw.get("skip_dirs", ["node_modules", ".next", ".git", "__pycache__"]),
            searchable_extensions=tools_raw.get("searchable_extensions", [
                ".js", ".jsx", ".ts", ".tsx", ".css", ".html",
                ".json", ".md", ".py", ".txt", ".env",
            ]),
        ),
        gradio=GradioConfig(
            height=gradio_raw.get("height", 700),
            share=gradio_raw.get("share", False),
        ),
    )
