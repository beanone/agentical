"""Common test fixtures for the entire test suite."""

import pytest
from typing import Any, Dict, List, Optional, Callable
from agentical.core.types import Tool, ToolParameter
from agentical.core import ProviderConfig, ProviderSettings, ToolRegistry, ToolExecutor


@pytest.fixture
def base_tool_parameter():
    """Base fixture for creating tool parameters.
    
    Returns:
        Callable: A factory function that creates ToolParameter instances with the given configuration.
        
    Example:
        def test_something(base_tool_parameter):
            param = base_tool_parameter(
                param_type="string",
                description="A test parameter",
                required=True,
                enum=["option1", "option2"]
            )
    """
    def _make_parameter(
        param_type: str = "string",
        description: str = "Test parameter",
        required: bool = True,
        enum: Optional[List[str]] = None,
        default: Any = None
    ) -> ToolParameter:
        return ToolParameter(
            type=param_type,
            description=description,
            required=required,
            enum=enum,
            default=default
        )
    return _make_parameter


@pytest.fixture
def base_tool():
    """Base fixture for creating tools.
    
    Returns:
        Callable: A factory function that creates Tool instances with the given configuration.
        
    Example:
        def test_something(base_tool, base_tool_parameter):
            param = base_tool_parameter(param_type="string", description="Input text")
            tool = base_tool(
                name="test_tool",
                description="A test tool",
                parameters={"input": param}
            )
    """
    def _make_tool(
        name: str,
        description: str,
        parameters: Dict[str, ToolParameter]
    ) -> Tool:
        return Tool(
            name=name,
            description=description,
            parameters=parameters
        )
    return _make_tool


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    """Fixture to ensure no environment variables affect tests.
    
    This fixture runs automatically for all tests to ensure a clean environment.
    """
    env_vars = [
        "OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL",
        "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL",
        "OLLAMA_MODEL", "OLLAMA_API_URL",
        "GEMINI_API_KEY", "GEMINI_MODEL", "GEMINI_BASE_URL"
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def base_provider_settings():
    """Base fixture for provider settings.
    
    Returns:
        Callable: A factory function that creates ProviderSettings instances with the given configuration.
        
    Example:
        def test_something(base_provider_settings):
            settings = base_provider_settings(
                provider_type="openai",
                api_key="test-key",
                model="gpt-4"
            )
    """
    def _make_settings(
        provider_type: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> ProviderSettings:
        settings = ProviderSettings(env_file=None)
        
        if provider_type == "openai":
            settings.openai_api_key = api_key
            settings.openai_model = model or "gpt-4-turbo-preview"
            settings.openai_base_url = base_url
        elif provider_type == "anthropic":
            settings.anthropic_api_key = api_key
            settings.anthropic_model = model or "claude-3-sonnet-20240229"
        elif provider_type == "ollama":
            settings.ollama_model = model or "llama2"
            settings.ollama_api_url = base_url or "http://localhost:11434"
        elif provider_type == "gemini":
            settings.gemini_api_key = api_key
            settings.gemini_model = model
            settings.gemini_base_url = base_url
            
        return settings
    return _make_settings


@pytest.fixture
def base_provider_config():
    """Base fixture for provider configuration.
    
    Returns:
        Callable: A factory function that creates ProviderConfig instances with the given configuration.
        
    Example:
        def test_something(base_provider_config):
            config = base_provider_config(
                provider_type="openai",
                api_key="test-key",
                model="gpt-4"
            )
    """
    def _make_config(
        provider_type: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        extra_config: Dict[str, Any] = None
    ) -> ProviderConfig:
        settings = ProviderSettings(env_file=None)
        
        if api_key:
            if provider_type == "openai":
                settings.openai_api_key = api_key
            elif provider_type == "anthropic":
                settings.anthropic_api_key = api_key
            elif provider_type == "gemini":
                settings.gemini_api_key = api_key
                
        if model:
            if provider_type == "openai":
                settings.openai_model = model
            elif provider_type == "anthropic":
                settings.anthropic_model = model
            elif provider_type == "ollama":
                settings.ollama_model = model
            elif provider_type == "gemini":
                settings.gemini_model = model
                
        if base_url:
            if provider_type == "openai":
                settings.openai_base_url = base_url
            elif provider_type == "ollama":
                settings.ollama_api_url = base_url
            elif provider_type == "gemini":
                settings.gemini_base_url = base_url
                
        config = ProviderConfig.from_settings(provider_type, settings)
        if extra_config:
            config.extra_config = extra_config
            
        return config
    return _make_config


@pytest.fixture
def base_tool_executor():
    """Base fixture for tool executor with mock handlers.
    
    Returns:
        Callable: A factory function that creates ToolExecutor instances with registered tools and handlers.
        
    Example:
        def test_something(base_tool_executor, sample_tools):
            async def handler(params):
                return f"Result: {params['input']}"
            
            executor = base_tool_executor(
                tools=sample_tools,
                handlers={"test_tool": handler}
            )
    """
    def _make_executor(
        tools: List[Tool],
        handlers: Dict[str, Callable]
    ) -> ToolExecutor:
        registry = ToolRegistry()
        for tool in tools:
            registry.register_tool(tool)
            
        executor = ToolExecutor(registry)
        for name, handler in handlers.items():
            executor.register_handler(name, handler)
            
        return executor
    return _make_executor


@pytest.fixture
def mock_async_handler():
    """Base fixture for creating mock async handlers.
    
    Returns:
        Callable: A factory function that creates async mock handlers with configurable return values.
        
    Example:
        def test_something(mock_async_handler):
            handler = mock_async_handler("Success!")
            result = await handler({"input": "test"})  # Returns "Success!"
    """
    def _make_handler(return_value: Any = None, error: Optional[Exception] = None):
        async def handler(params: Dict[str, Any]) -> Any:
            if error:
                raise error
            return return_value
        return handler
    return _make_handler


@pytest.fixture
def base_tool_registry():
    """Base fixture for creating tool registries.
    
    Returns:
        Callable: A factory function that creates ToolRegistry instances with registered tools.
        
    Example:
        def test_something(base_tool_registry, sample_tools):
            registry = base_tool_registry(tools=sample_tools)
    """
    def _make_registry(tools: List[Tool]) -> ToolRegistry:
        registry = ToolRegistry()
        for tool in tools:
            registry.register_tool(tool)
        return registry
    return _make_registry 