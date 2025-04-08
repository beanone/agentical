# Error Handling

This document covers error handling in Agentical.

## Exception Hierarchy

```python
class AgenticalError(Exception):
    """Base exception for all Agentical errors."""
    pass

class ConfigurationError(AgenticalError):
    """Error in configuration loading or validation."""
    pass

class ConnectionError(AgenticalError):
    """Error in server connection or communication."""
    pass

class ToolExecutionError(AgenticalError):
    """Error during tool execution."""
    pass

class LLMError(AgenticalError):
    """Error in LLM processing."""
    pass
```

## Connection Error Handling

The framework implements robust connection error handling:

```python
class MCPConnectionService:
    async def connect(self, server_name: str, config: ServerConfig):
        try:
            session = await self._connect_with_retry(server_name, config)
            await self._start_health_monitoring(session)
            return session
        except Exception as e:
            logger.error(
                "Connection failed",
                extra={
                    "server": server_name,
                    "error": str(e)
                }
            )
            raise ConnectionError(f"Failed to connect to {server_name}: {e}")
```

### Reconnection Strategy

1. **Exponential Backoff**
```python
class ServerReconnector:
    BASE_DELAY = 1.0  # Initial delay in seconds
    MAX_RETRIES = 3   # Maximum number of retry attempts

    async def _connect_with_retry(self, server_name: str, config: ServerConfig):
        delay = self.BASE_DELAY
        for attempt in range(self.MAX_RETRIES):
            try:
                return await self._establish_connection(server_name, config)
            except Exception as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
```

2. **Health Monitoring**
```python
class HealthMonitor:
    HEARTBEAT_INTERVAL = 30  # seconds
    MAX_HEARTBEAT_MISS = 2   # attempts before reconnection

    async def monitor_health(self, session):
        misses = 0
        while True:
            try:
                await session.heartbeat()
                misses = 0
            except Exception:
                misses += 1
                if misses >= self.MAX_HEARTBEAT_MISS:
                    await self._trigger_reconnection(session)
            await asyncio.sleep(self.HEARTBEAT_INTERVAL)
```

## Resource Management

The framework uses `AsyncExitStack` for guaranteed resource cleanup:

```python
class MCPToolProvider:
    def __init__(self):
        self.exit_stack = AsyncExitStack()

    async def cleanup(self, server_name: str | None = None):
        """Clean up resources for a specific server or all servers."""
        try:
            if server_name:
                await self._cleanup_server(server_name)
            else:
                await self.exit_stack.aclose()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            raise
```

## Tool Execution Error Handling

```python
async def execute_tool(tool: Tool, **kwargs) -> CallToolResult:
    try:
        # Validate parameters
        validate_parameters(tool, kwargs)

        # Execute tool
        result = await tool.execute(**kwargs)

        return CallToolResult(
            success=True,
            output=result
        )
    except ValidationError as e:
        return CallToolResult(
            success=False,
            error=f"Parameter validation failed: {e}"
        )
    except Exception as e:
        return CallToolResult(
            success=False,
            error=f"Tool execution failed: {e}"
        )
```

## LLM Error Handling

```python
class OpenAIBackend(LLMBackend):
    async def process_query(self, query: str, tools: list[Tool], execute_tool: callable):
        try:
            # Process with OpenAI
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": query}],
                tools=self.convert_tools(tools)
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI processing error: {e}")
            raise LLMError(f"Failed to process query: {e}")
```

## Logging Strategy

The framework implements comprehensive logging:

```python
import logging
from agentical.utils.log_utils import sanitize_log_message

logger = logging.getLogger(__name__)

# Example logging pattern
try:
    result = await operation()
    logger.info(
        "Operation successful",
        extra={
            "operation": "name",
            "duration_ms": duration,
            "result": sanitize_log_message(str(result))
        }
    )
except Exception as e:
    logger.error(
        "Operation failed",
        extra={
            "operation": "name",
            "error": sanitize_log_message(str(e))
        },
        exc_info=True
    )
```

## Best Practices

1. **Exception Handling**
   - Use specific exception types
   - Provide clear error messages
   - Include context in exceptions
   - Proper exception propagation

2. **Resource Management**
   - Use context managers
   - Implement proper cleanup
   - Handle cleanup errors
   - Log cleanup operations

3. **Error Recovery**
   - Implement retry mechanisms
   - Use exponential backoff
   - Monitor system health
   - Graceful degradation

4. **Logging**
   - Structured logging format
   - Appropriate log levels
   - Sanitize sensitive data
   - Include relevant context