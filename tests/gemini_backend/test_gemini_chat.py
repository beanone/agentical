"""Unit tests for Gemini backend implementation."""

import os
import pytest
from unittest.mock import AsyncMock, Mock, patch
from google import genai
from google.genai.types import Content, Part, GenerateContentResponse, Candidate

from agentical.gemini_backend.gemini_chat import GeminiBackend
from mcp.types import Tool as MCPTool, CallToolResult, TextContent

@pytest.fixture
def mock_genai_client():
    """Fixture providing a mock Gemini client."""
    with patch('google.genai.Client') as mock:
        yield mock

@pytest.fixture
def mock_env_vars():
    """Fixture to set and cleanup environment variables."""
    original_env = dict(os.environ)
    os.environ['GEMINI_API_KEY'] = 'test_key'
    os.environ['GEMINI_MODEL'] = 'test_model'
    yield
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture
def mock_mcp_tools():
    """Fixture providing mock MCP tools."""
    return [
        MCPTool(
            name="tool1",
            description="Test tool 1",
            parameters={},
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string"}
                },
                "required": ["param1"]
            }
        ),
        MCPTool(
            name="tool2",
            description="Test tool 2",
            parameters={},
            inputSchema={
                "type": "object",
                "properties": {
                    "param2": {"type": "integer"}
                }
            }
        )
    ]

def test_init_with_api_key():
    """Test initialization with explicit API key."""
    backend = GeminiBackend(api_key="test_key")
    assert backend.model == GeminiBackend.DEFAULT_MODEL

def test_init_with_env_vars(mock_env_vars):
    """Test initialization with environment variables."""
    backend = GeminiBackend()
    assert backend.model == "test_model"

def test_init_without_api_key():
    """Test initialization fails without API key."""
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]
    
    with pytest.raises(ValueError, match="GEMINI_API_KEY not found"):
        GeminiBackend()

def test_init_with_invalid_api_key(mock_genai_client):
    """Test initialization with invalid API key."""
    mock_genai_client.side_effect = Exception("Invalid API key")
    
    with pytest.raises(ValueError, match="Failed to initialize Gemini client"):
        GeminiBackend(api_key="invalid_key")

def test_convert_tools_success(mock_env_vars, mock_mcp_tools):
    """Test successful conversion of MCP tools to Gemini format."""
    backend = GeminiBackend()
    result = backend.convert_tools(mock_mcp_tools)
    
    assert isinstance(result, list)
    assert len(result) == len(mock_mcp_tools)
    for tool in result:
        assert isinstance(tool, genai.types.Tool)
        assert len(tool.function_declarations) == 1
        func_decl = tool.function_declarations[0]
        assert isinstance(func_decl, genai.types.FunctionDeclaration)
        assert func_decl.name in ["tool1", "tool2"]
        assert isinstance(func_decl.parameters, genai.types.Schema)

def test_convert_tools_empty_list(mock_env_vars):
    """Test conversion of empty tools list."""
    backend = GeminiBackend()
    result = backend.convert_tools([])
    
    assert isinstance(result, list)
    assert len(result) == 0

def test_convert_tools_error(mock_env_vars, mock_mcp_tools):
    """Test error handling during tool conversion."""
    backend = GeminiBackend()
    
    # Create an invalid tool that will cause conversion to fail
    invalid_tool = MCPTool(
        name="invalid_tool",
        description="Invalid tool",
        parameters={},
        inputSchema={
            "type": "object",
            "properties": {
                "param": {"type": "string", "enum": [1, 2, 3]}  # Type mismatch in enum values
            }
        }
    )
    
    with pytest.raises(ValueError):  # Gemini's FunctionDeclaration raises ValueError for invalid schemas
        backend.convert_tools([invalid_tool])

@pytest.mark.asyncio
async def test_process_query_without_tool_calls(mock_env_vars, mock_genai_client, mock_mcp_tools):
    """Test processing a query that doesn't require tool calls."""
    # Setup mock response
    mock_part = Part(text="Test response")
    mock_content = Content(parts=[mock_part], role="model")
    mock_candidate = Candidate(content=mock_content, finish_reason="stop")
    mock_response = GenerateContentResponse(candidates=[mock_candidate])
    
    # Configure mock client
    mock_client = Mock()
    mock_client.models.generate_content = Mock(return_value=mock_response)
    mock_genai_client.return_value = mock_client
    
    # Execute test
    backend = GeminiBackend()
    response = await backend.process_query(
        query="test query",
        tools=mock_mcp_tools,
        execute_tool=AsyncMock()
    )
    
    assert response == "Test response"
    mock_client.models.generate_content.assert_called_once()

@pytest.mark.asyncio
async def test_process_query_with_tool_calls(mock_env_vars, mock_genai_client, mock_mcp_tools):
    """Test processing a query that requires tool calls."""
    # First response with tool call
    mock_tool_part = Part(
        function_call={"name": "tool1", "args": {"param1": "test"}}
    )
    mock_content1 = Content(parts=[mock_tool_part], role="model")
    mock_candidate1 = Candidate(content=mock_content1, finish_reason="stop")
    mock_response1 = GenerateContentResponse(candidates=[mock_candidate1])
    
    # Second response with final answer
    mock_final_part = Part(text="Final response")
    mock_content2 = Content(parts=[mock_final_part], role="model")
    mock_candidate2 = Candidate(content=mock_content2, finish_reason="stop")
    mock_response2 = GenerateContentResponse(candidates=[mock_candidate2])
    
    # Configure mock client
    mock_client = Mock()
    mock_client.models.generate_content = Mock(side_effect=[mock_response1, mock_response2])
    mock_genai_client.return_value = mock_client
    
    # Mock tool execution
    mock_execute_tool = AsyncMock(return_value=CallToolResult(
        content=[TextContent(type="text", text="Tool result")]
    ))
    
    # Execute test
    backend = GeminiBackend()
    response = await backend.process_query(
        query="test query",
        tools=mock_mcp_tools,
        execute_tool=mock_execute_tool
    )
    
    assert response == "Final response"
    assert mock_client.models.generate_content.call_count == 2
    mock_execute_tool.assert_called_once_with("tool1", {"param1": "test"})

@pytest.mark.asyncio
async def test_process_query_with_tool_error(mock_env_vars, mock_genai_client, mock_mcp_tools):
    """Test handling of tool execution errors."""
    # First response with tool call
    mock_tool_part = Part(
        function_call={"name": "tool1", "args": {"param1": "test"}}
    )
    mock_content1 = Content(parts=[mock_tool_part], role="model")
    mock_candidate1 = Candidate(content=mock_content1, finish_reason="stop")
    mock_response1 = GenerateContentResponse(candidates=[mock_candidate1])
    
    # Second response with error handling
    mock_final_part = Part(text="Error handled response")
    mock_content2 = Content(parts=[mock_final_part], role="model")
    mock_candidate2 = Candidate(content=mock_content2, finish_reason="stop")
    mock_response2 = GenerateContentResponse(candidates=[mock_candidate2])
    
    # Configure mock client
    mock_client = Mock()
    mock_client.models.generate_content = Mock(side_effect=[mock_response1, mock_response2])
    mock_genai_client.return_value = mock_client
    
    # Mock tool execution to raise error
    mock_execute_tool = AsyncMock(side_effect=ValueError("Tool execution failed"))
    
    # Execute test
    backend = GeminiBackend()
    response = await backend.process_query(
        query="test query",
        tools=mock_mcp_tools,
        execute_tool=mock_execute_tool
    )
    
    assert response == "Error handled response"
    mock_execute_tool.assert_called_once_with("tool1", {"param1": "test"})

@pytest.mark.asyncio
async def test_process_query_with_no_candidates(mock_env_vars, mock_genai_client, mock_mcp_tools):
    """Test handling of response with no candidates."""
    # Setup mock response with no candidates
    mock_response = GenerateContentResponse(candidates=[])
    
    # Configure mock client
    mock_client = Mock()
    mock_client.models.generate_content = Mock(return_value=mock_response)
    mock_genai_client.return_value = mock_client
    
    # Execute test
    backend = GeminiBackend()
    response = await backend.process_query(
        query="test query",
        tools=mock_mcp_tools,
        execute_tool=AsyncMock()
    )
    
    assert response == "No response generated"
    mock_client.models.generate_content.assert_called_once()

@pytest.mark.asyncio
async def test_process_query_with_context(mock_env_vars, mock_genai_client, mock_mcp_tools):
    """Test processing a query with conversation context."""
    # Setup context
    context = [
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"}
    ]
    
    # Setup mock response
    mock_part = Part(text="Response with context")
    mock_content = Content(parts=[mock_part], role="model")
    mock_candidate = Candidate(content=mock_content, finish_reason="stop")
    mock_response = GenerateContentResponse(candidates=[mock_candidate])
    
    # Configure mock client
    mock_client = Mock()
    mock_client.models.generate_content = Mock(return_value=mock_response)
    mock_genai_client.return_value = mock_client
    
    # Execute test
    backend = GeminiBackend()
    response = await backend.process_query(
        query="test query",
        tools=mock_mcp_tools,
        execute_tool=AsyncMock(),
        context=context
    )
    
    assert response == "Response with context"
    # Verify API call contents
    call_args = mock_client.models.generate_content.call_args[1]
    contents = call_args["contents"]
    
    # Verify the contents structure
    assert isinstance(contents, list)
    assert len(contents) == 3  # Two context messages + new query
    assert all(isinstance(content, (dict, Content)) for content in contents)
    
    # Verify the context messages are preserved
    assert contents[0]["role"] == "user"
    assert contents[0]["content"] == "Previous question"
    assert contents[1]["role"] == "assistant"
    assert contents[1]["content"] == "Previous answer"
    
    # Verify the new query is added
    assert isinstance(contents[2], Content)
    assert contents[2].role == "user"
    assert len(contents[2].parts) == 1
    assert contents[2].parts[0].text == "test query"

@pytest.mark.asyncio
async def test_process_query_with_api_error(mock_env_vars, mock_genai_client, mock_mcp_tools):
    """Test handling of API errors."""
    # Configure mock client to raise error
    mock_client = Mock()
    mock_client.models.generate_content = Mock(side_effect=Exception("API error"))
    mock_genai_client.return_value = mock_client
    
    # Execute test
    backend = GeminiBackend()
    with pytest.raises(ValueError, match="Error in Gemini conversation"):
        await backend.process_query(
            query="test query",
            tools=mock_mcp_tools,
            execute_tool=AsyncMock()
        ) 