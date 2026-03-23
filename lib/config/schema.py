"""
Dataclasses que definen la estructura tipada de la configuración.
"""
from dataclasses import dataclass, field


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
    max_tool_calls: int = 30  # Límite total de llamadas a herramientas por tarea


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
