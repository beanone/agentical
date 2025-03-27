"""Tests for provider configuration module."""

import pytest
import os
from agentical.core import ProviderSettings, ProviderConfig
from agentical.core import ProviderError


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    """Fixture to ensure no environment variables or .env file affect tests."""
    env_vars = [
        "OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL",
        "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL",
        "OLLAMA_MODEL", "OLLAMA_API_URL",
        "GEMINI_API_KEY", "GEMINI_MODEL", "GEMINI_BASE_URL"
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)
    return ProviderSettings(env_file=None)


def test_provider_settings_defaults():
    """Test default values in ProviderSettings."""
    settings = ProviderSettings(env_file=None)
    
    # Test OpenAI defaults
    assert settings.openai_api_key is None
    assert settings.openai_model == "gpt-4-turbo-preview"
    assert settings.openai_base_url is None
    
    # Test Anthropic defaults
    assert settings.anthropic_api_key is None
    assert settings.anthropic_model == "claude-3-sonnet-20240229"
    
    # Test Ollama defaults
    assert settings.ollama_model == "llama2"
    assert settings.ollama_api_url == "http://localhost:11434"
    
    # Test Gemini defaults
    assert settings.gemini_api_key is None
    assert settings.gemini_model is None
    assert settings.gemini_base_url is None


def test_provider_settings_from_env(monkeypatch):
    """Test loading settings from environment variables."""
    env_vars = {
        "OPENAI_API_KEY": "test-openai-key",
        "OPENAI_MODEL": "gpt-4",
        "OPENAI_BASE_URL": "https://api.test.com",
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "ANTHROPIC_MODEL": "claude-3",
        "OLLAMA_MODEL": "mistral",
        "OLLAMA_API_URL": "http://localhost:8000",
        "GEMINI_API_KEY": "test-gemini-key",
        "GEMINI_MODEL": "gemini-pro",
        "GEMINI_BASE_URL": "https://gemini.test.com"
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    settings = ProviderSettings(env_file=None)
    
    # Test OpenAI settings
    assert settings.openai_api_key == "test-openai-key"
    assert settings.openai_model == "gpt-4"
    assert settings.openai_base_url == "https://api.test.com"
    
    # Test Anthropic settings
    assert settings.anthropic_api_key == "test-anthropic-key"
    assert settings.anthropic_model == "claude-3"
    
    # Test Ollama settings
    assert settings.ollama_model == "mistral"
    assert settings.ollama_api_url == "http://localhost:8000"
    
    # Test Gemini settings
    assert settings.gemini_api_key == "test-gemini-key"
    assert settings.gemini_model == "gemini-pro"
    assert settings.gemini_base_url == "https://gemini.test.com"


def test_provider_config_defaults():
    """Test default values in ProviderConfig."""
    config = ProviderConfig()
    
    assert config.api_key is None
    assert config.model is None
    assert config.base_url is None
    assert config.extra_config == {}


@pytest.mark.parametrize("provider,expected", [
    ("openai", {
        "api_key": "test-key",
        "model": "gpt-4-turbo-preview",
        "base_url": "https://test.com"
    }),
    ("anthropic", {
        "api_key": "test-key",
        "model": "claude-3-sonnet-20240229",
        "base_url": None
    }),
    ("ollama", {
        "api_key": None,
        "model": "llama2",
        "base_url": "http://localhost:11434"
    }),
    ("gemini", {
        "api_key": "test-key",
        "model": "gemini-pro",
        "base_url": "https://test.com"
    })
])
def test_provider_config_from_settings(provider, expected):
    """Test creating ProviderConfig from settings for different providers."""
    settings = ProviderSettings(env_file=None)
    
    # Set test values in settings
    if provider == "openai":
        settings.openai_api_key = "test-key"
        settings.openai_base_url = "https://test.com"
    elif provider == "anthropic":
        settings.anthropic_api_key = "test-key"
    elif provider == "gemini":
        settings.gemini_api_key = "test-key"
        settings.gemini_model = "gemini-pro"
        settings.gemini_base_url = "https://test.com"
    
    config = ProviderConfig.from_settings(provider, settings)
    
    assert config.api_key == expected["api_key"]
    assert config.model == expected["model"]
    assert config.base_url == expected["base_url"]


def test_provider_config_invalid_provider():
    """Test error handling for invalid provider."""
    with pytest.raises(ProviderError) as exc:
        ProviderConfig.from_settings("invalid", ProviderSettings(env_file=None))
    assert "Unsupported provider: invalid" in str(exc.value)


@pytest.mark.parametrize("config,expected", [
    # Valid configurations
    (
        {"model": "gpt-4", "api_key": "test-key"},
        True
    ),
    (
        {"model": "llama2"},  # Local model doesn't need API key
        True
    ),
    # Invalid configurations
    (
        {"model": None, "api_key": "test-key"},
        False
    ),
    (
        {"model": "gpt-4", "api_key": None},  # Missing required API key
        False
    ),
    (
        {"model": "claude-3", "api_key": None},  # Missing required API key
        False
    ),
    (
        {"model": "gemini-pro", "api_key": None},  # Missing required API key
        False
    )
])
def test_provider_config_is_configured(config, expected):
    """Test is_configured property for various configurations."""
    provider_config = ProviderConfig(**config)
    assert provider_config.is_configured == expected 