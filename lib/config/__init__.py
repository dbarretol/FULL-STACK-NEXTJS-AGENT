"""
Carga y expone la configuración central desde settings.yaml.
Uso: from lib.config import cfg
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
import yaml

_CONFIG_PATH = Path(__file__).parent / "settings.yaml"


@dataclass
class ModelConfig:
    model_id: str
    temperature: float = 0.2
    max_tokens: int = 4096
    region_name: str = "us-east-1"
    streaming: bool = True
    max_completion_tokens: int = 4096


@dataclass
class AgentConfig:
    max_handler_calls: int = 30


@dataclass
class ContextConfig:
    max_tokens: int = 40_000
    compression_ratio: float = 0.70
    chars_per_token: int = 4


@dataclass
class SandboxConfig:
    timeout_seconds: int = 3600


@dataclass
class ToolsConfig:
    max_read_chars: int = 50_000
    max_write_chars: int = 1_000_000
    search_max_results: int = 20
    glob_max_results: int = 100
    skip_dirs: list[str] = field(default_factory=lambda: ["node_modules", ".next", ".git", "__pycache__"])
    searchable_extensions: list[str] = field(default_factory=lambda: [
        ".js", ".jsx", ".ts", ".tsx", ".css", ".html",
        ".json", ".md", ".py", ".txt", ".env",
    ])


@dataclass
class GradioConfig:
    height: int = 700
    share: bool = False


@dataclass
class Settings:
    llm_provider: str
    model: ModelConfig
    agent: AgentConfig
    context: ContextConfig
    sandbox: SandboxConfig
    tools: ToolsConfig
    gradio: GradioConfig


def _load() -> Settings:
    """Carga settings.yaml y construye el objeto Settings."""
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    provider = raw.get("llm_provider", "bedrock")
    model_raw = raw.get("models", {}).get(provider, {})

    # AWS_REGION env var sobreescribe region_name del YAML
    region = os.getenv("AWS_REGION", model_raw.get("region_name", "us-east-1"))

    model_cfg = ModelConfig(
        model_id=model_raw.get("model_id", "amazon.nova-pro-v1:0"),
        temperature=model_raw.get("temperature", 0.2),
        max_tokens=model_raw.get("max_tokens", 4096),
        region_name=region,
        streaming=model_raw.get("streaming", True),
        max_completion_tokens=model_raw.get("max_completion_tokens", 4096),
    )

    agent_raw = raw.get("agent", {})
    ctx_raw = raw.get("context", {})
    sbx_raw = raw.get("sandbox", {})
    tools_raw = raw.get("tools", {})
    gradio_raw = raw.get("gradio", {})

    return Settings(
        llm_provider=provider,
        model=model_cfg,
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


# Singleton: importar desde cualquier módulo con `from lib.config import cfg`
cfg: Settings = _load()
