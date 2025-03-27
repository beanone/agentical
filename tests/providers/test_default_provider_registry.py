"""Tests for default provider registry."""

import pytest
from unittest.mock import Mock, patch
from agentical.core import ProviderConfig, ToolExecutor
from agentical.providers import DefaultProviderRegistry
from agentical.providers.openai import OpenAIProvider
from agentical.providers.anthropic import AnthropicProvider


@pytest.fixture
def config():
    """Fixture for provider config."""
    return ProviderConfig(
        api_key="test-key",
        model="gpt-4"
    )


@pytest.fixture
def executor():
    """Fixture for tool executor."""
    return Mock(spec=ToolExecutor)


@pytest.fixture(autouse=True)
def clear_singleton():
    """Clear the singleton instance before each test."""
    DefaultProviderRegistry._instance = None
    yield


def test_singleton_behavior(config, executor):
    """Test that DefaultProviderRegistry behaves as a singleton."""
    registry1 = DefaultProviderRegistry(config, executor)
    registry2 = DefaultProviderRegistry(config, executor)
    
    assert registry1 is registry2


def test_provider_initialization(config, executor):
    """Test that providers are properly initialized."""
    with patch('agentical.providers.default_provider_registry.OpenAIProvider') as mock_openai, \
         patch('agentical.providers.default_provider_registry.AnthropicProvider') as mock_anthropic:
        
        # Setup mocks
        mock_openai_instance = Mock(spec=OpenAIProvider)
        mock_openai_instance.get_name.return_value = "openai"
        mock_openai.return_value = mock_openai_instance
        
        mock_anthropic_instance = Mock(spec=AnthropicProvider)
        mock_anthropic_instance.get_name.return_value = "anthropic"
        mock_anthropic.return_value = mock_anthropic_instance
        
        # Create registry
        registry = DefaultProviderRegistry(config, executor)
        
        # Verify providers were initialized
        mock_openai.assert_called_once_with(config, executor)
        mock_anthropic.assert_called_once_with(config, executor)
        
        # Verify providers were stored
        assert registry.get_provider("openai") is mock_openai_instance
        assert registry.get_provider("anthropic") is mock_anthropic_instance


def test_get_provider_success(config, executor):
    """Test successful provider retrieval."""
    registry = DefaultProviderRegistry(config, executor)
    
    # Get providers
    openai_provider = registry.get_provider("openai")
    anthropic_provider = registry.get_provider("anthropic")
    
    # Verify correct types
    assert isinstance(openai_provider, OpenAIProvider)
    assert isinstance(anthropic_provider, AnthropicProvider)


def test_get_provider_not_found(config, executor):
    """Test error handling for unknown provider."""
    registry = DefaultProviderRegistry(config, executor)
    
    with pytest.raises(KeyError) as exc:
        registry.get_provider("unknown")
    assert "Provider 'unknown' not found" in str(exc.value)


def test_singleton_state_preservation(config, executor):
    """Test that singleton preserves state across instantiations."""
    # Create first instance
    registry1 = DefaultProviderRegistry(config, executor)
    provider1 = registry1.get_provider("openai")
    
    # Create second instance
    registry2 = DefaultProviderRegistry(config, executor)
    provider2 = registry2.get_provider("openai")
    
    # Verify same provider instance is returned
    assert provider1 is provider2 