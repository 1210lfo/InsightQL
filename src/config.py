"""
Configuration module for InsightQL
Loads environment variables and provides typed configuration.
"""

import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass
class GitHubModelsConfig:
    """GitHub Models configuration"""
    token: str = field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))
    model: str = field(default_factory=lambda: os.getenv("GITHUB_MODEL", "gpt-4o"))
    endpoint: str = field(default_factory=lambda: os.getenv("GITHUB_MODELS_ENDPOINT", "https://models.inference.ai.azure.com"))


@dataclass
class GeminiConfig:
    """Gemini LLM configuration (deprecated - using GitHub Models)"""
    api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))


@dataclass
class SupabaseConfig:
    """Supabase connection configuration"""
    url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    anon_key: str = field(default_factory=lambda: os.getenv("SUPABASE_ANON_KEY", ""))
    service_role_key: str = field(default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
    project_ref: str = field(default_factory=lambda: os.getenv("SUPABASE_PROJECT_REF", ""))
    access_token: str = field(default_factory=lambda: os.getenv("SUPABASE_ACCESS_TOKEN", ""))


@dataclass
class MCPConfig:
    """MCP Server configuration"""
    endpoint: str = field(
        default_factory=lambda: os.getenv("MCP_ENDPOINT", "https://mcp.supabase.com/mcp")
    )
    timeout_ms: int = field(
        default_factory=lambda: int(os.getenv("AGENT_TIMEOUT_MS", "30000"))
    )


@dataclass
class AgentConfig:
    """Agent behavior configuration"""
    max_retries: int = field(
        default_factory=lambda: int(os.getenv("AGENT_MAX_RETRIES", "2"))
    )
    cache_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("AGENT_CACHE_TTL_SECONDS", "3600"))
    )
    allowed_rpc_functions: List[str] = field(default_factory=list)
    # API rate limiting
    max_requests_per_minute: int = field(
        default_factory=lambda: int(os.getenv("MAX_REQUESTS_PER_MINUTE", "30"))
    )
    # LLM spending limits
    max_tokens_per_request: int = field(
        default_factory=lambda: int(os.getenv("MAX_TOKENS_PER_REQUEST", "4000"))
    )
    max_daily_requests: int = field(
        default_factory=lambda: int(os.getenv("MAX_DAILY_REQUESTS", "1000"))
    )
    
    def __post_init__(self):
        if not self.allowed_rpc_functions:
            allowed = os.getenv("ALLOWED_RPC_FUNCTIONS", "")
            self.allowed_rpc_functions = [f.strip() for f in allowed.split(",") if f.strip()]


@dataclass
class VoiceConfig:
    """Voice / Speech-to-Text configuration (Groq Whisper)"""
    enabled: bool = field(
        default_factory=lambda: os.getenv("VOICE_ENABLED", "false").lower() == "true"
    )
    provider: str = field(
        default_factory=lambda: os.getenv("VOICE_PROVIDER", "groq")
    )
    groq_api_key: str = field(
        default_factory=lambda: os.getenv("GROQ_API_KEY", "")
    )
    whisper_model: str = field(
        default_factory=lambda: os.getenv("WHISPER_MODEL", "whisper-large-v3-turbo")
    )
    language: str = field(
        default_factory=lambda: os.getenv("VOICE_LANGUAGE", "es")
    )
    max_audio_duration_seconds: int = field(
        default_factory=lambda: int(os.getenv("MAX_AUDIO_DURATION_SECONDS", "60"))
    )


@dataclass
class LangSmithConfig:
    """LangSmith tracing configuration"""
    enabled: bool = field(
        default_factory=lambda: os.getenv("LANGSMITH_TRACING", "true").lower() == "true"
    )
    api_key: str = field(
        default_factory=lambda: os.getenv("LANGSMITH_API_KEY", "")
    )
    project: str = field(
        default_factory=lambda: os.getenv("LANGSMITH_PROJECT", "InsightQL")
    )
    endpoint: str = field(
        default_factory=lambda: os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    )


@dataclass
class ObservabilityConfig:
    """Legacy OpenTelemetry configuration (deprecated)"""
    enabled: bool = field(
        default_factory=lambda: os.getenv("ENABLE_TRACING", "false").lower() == "true"
    )
    otlp_endpoint: str = field(
        default_factory=lambda: os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    )
    service_name: str = field(
        default_factory=lambda: os.getenv("OTEL_SERVICE_NAME", "insightql-agent")
    )


@dataclass
class Config:
    """Main configuration container"""
    github_models: GitHubModelsConfig = field(default_factory=GitHubModelsConfig)
    gemini: GeminiConfig = field(default_factory=GeminiConfig)
    supabase: SupabaseConfig = field(default_factory=SupabaseConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    langsmith: LangSmithConfig = field(default_factory=LangSmithConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)


# Singleton instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config() -> Config:
    """Reload configuration from environment."""
    global _config
    load_dotenv(override=True)
    _config = Config()
    return _config
