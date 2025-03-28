"""Provider configuration module.

This module provides configuration management for LLM providers,
with support for reading from environment variables.
"""

from typing import Optional, Dict, Any, Literal
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings
from dataclasses import dataclass, field
import os

from .errors import ConfigError


class ProviderError(Exception):
    """Raised when there is an error with provider configuration."""
    pass


ProviderType = Literal["openai", "anthropic", "ollama", "gemini"]


class ProviderSettings(BaseSettings):
    """Global settings for all LLM providers.
    
    This class manages configuration for all supported LLM providers.
    Each provider can have its own specific settings.
    
    Add new provider configurations here as needed.
    """
    
    # OpenAI settings
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    openai_model: str = Field("gpt-4-turbo-preview", description="Default OpenAI model")
    openai_base_url: Optional[str] = Field(None, description="Optional OpenAI API base URL")
    
    # Anthropic settings
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    anthropic_model: str = Field("claude-3-sonnet-20240229", description="Default Anthropic model")
    
    # Ollama settings
    ollama_model: str = Field("llama2", description="Default Ollama model")
    ollama_api_url: str = Field("http://localhost:11434", description="Ollama API URL")
    
    # Gemini settings
    gemini_api_key: Optional[str] = Field(None, description="Google Gemini API key")
    gemini_model: Optional[str] = Field(None, description="Gemini model name")
    gemini_base_url: Optional[str] = Field(None, description="Optional Gemini API base URL")
    
    def __init__(self, env_file: Optional[str] = None, **kwargs):
        """Initialize settings with optional custom .env file path.
        
        Args:
            env_file: Optional path to .env file. If not provided, defaults to ".env"
            **kwargs: Additional keyword arguments passed to BaseSettings
        """
        # Always update env_file in model_config, even if None
        self.model_config.update({"env_file": env_file})
        super().__init__(**kwargs)
    
    model_config = ConfigDict(
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"  # Allow extra fields for future extensibility
    )




@dataclass
class ProviderConfig:
    """Configuration for a specific LLM provider instance.
    
    This class holds the configuration for a specific provider instance,
    extracted from the global settings.
    
    Attributes:
        api_key: The API key for the provider
        model: The model name to use
        base_url: Optional base URL for the API
        extra_config: Additional provider-specific configuration
    """
    
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    extra_config: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_settings(cls, provider: ProviderType, settings: Optional[ProviderSettings] = None) -> "ProviderConfig":
        """Create a provider config from settings.
        
        Args:
            provider: The provider to load config for
            settings: Optional settings instance, will load from env if not provided
            
        Returns:
            A configured ProviderConfig instance
            
        Raises:
            ConfigError: If provider is not supported
        """
        if settings is None:
            settings = ProviderSettings()
            
        provider_configs = {
            "openai": lambda: cls(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
                base_url=settings.openai_base_url
            ),
            "anthropic": lambda: cls(
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_model
            ),
            "ollama": lambda: cls(
                model=settings.ollama_model,
                base_url=settings.ollama_api_url
            ),
            "gemini": lambda: cls(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
                base_url=settings.gemini_base_url
            )
        }
        
        if provider not in provider_configs:
            raise ConfigError(f"Unsupported provider: {provider}", provider_name=provider)
            
        return provider_configs[provider]()
            
    @property
    def is_configured(self) -> bool:
        """Check if the provider is properly configured.
        
        Returns:
            True if required settings are present, False otherwise
        """
        # Base check for required fields
        if self.model is None:
            return False
            
        # API key is required for cloud providers
        cloud_models = ["gpt-", "claude-", "gemini-"]
        if any(self.model.startswith(prefix) for prefix in cloud_models) and not self.api_key:
            return False
            
        return True 