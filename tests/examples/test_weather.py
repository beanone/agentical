"""Tests for the weather tool."""

import os
import pytest
from typing import Dict, Any
from unittest.mock import AsyncMock, patch, MagicMock

from examples.tools.weather_tool import (
    WeatherError,
    create_weather_tool,
    weather_handler,
    _get_weather_data,
    _format_weather_response
)


@pytest.fixture
def mock_weather_response() -> Dict[str, Any]:
    """Create a mock weather API response."""
    return {
        "name": "London",
        "sys": {
            "country": "GB"
        },
        "weather": [{
            "main": "Clear",
            "description": "clear sky"
        }],
        "main": {
            "temp": 20,
            "feels_like": 19,
            "humidity": 65
        },
        "wind": {
            "speed": 5
        }
    }


@pytest.fixture
def mock_aiohttp_response(mock_weather_response: Dict[str, Any]) -> AsyncMock:
    """Create a mock aiohttp response."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_weather_response)
    mock_response.text = AsyncMock(return_value="Not found")
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock()
    return mock_response


@pytest.fixture
def mock_aiohttp_session(mock_aiohttp_response: AsyncMock) -> AsyncMock:
    """Create a mock aiohttp session."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_aiohttp_response)
    return mock_session


def test_create_weather_tool() -> None:
    """Test creating the weather tool definition."""
    tool = create_weather_tool()
    
    # Verify tool properties
    assert tool.name == "get_weather"
    assert "weather information" in tool.description.lower()
    
    # Verify parameters
    params = tool.parameters
    assert "location" in params
    assert "units" in params
    
    # Verify location parameter
    assert params["location"].type == "string"
    assert params["location"].required is True
    
    # Verify units parameter
    assert params["units"].type == "string"
    assert params["units"].required is False
    assert params["units"].enum == ["metric", "imperial"]
    assert params["units"].default == "metric"


@pytest.mark.asyncio
async def test_weather_handler_missing_api_key() -> None:
    """Test that handler raises error when API key is missing."""
    with patch.dict(os.environ, clear=True):
        with pytest.raises(WeatherError, match="API key not found"):
            await weather_handler({"location": "London"})


@pytest.mark.asyncio
async def test_weather_handler_missing_location() -> None:
    """Test that handler raises error when location is missing."""
    with patch.dict(os.environ, {"OPENWEATHERMAP_API_KEY": "test_key"}):
        with pytest.raises(WeatherError, match="Location parameter is required"):
            await weather_handler({})


@pytest.mark.asyncio
async def test_weather_handler_invalid_units() -> None:
    """Test that handler raises error with invalid units."""
    with patch.dict(os.environ, {"OPENWEATHERMAP_API_KEY": "test_key"}):
        with pytest.raises(WeatherError, match="Units must be either 'metric' or 'imperial'"):
            await weather_handler({
                "location": "London",
                "units": "invalid"
            })


@pytest.mark.asyncio
async def test_get_weather_data(mock_weather_response: Dict[str, Any], mock_aiohttp_session: AsyncMock) -> None:
    """Test getting weather data from the API."""
    with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
        result = await _get_weather_data(
            location="London",
            units="metric",
            api_key="test_key"
        )
        
        assert result == mock_weather_response
        
        # Verify API call
        mock_aiohttp_session.get.assert_called_once()
        call_args = mock_aiohttp_session.get.call_args[0][0]
        assert "api.openweathermap.org" in call_args
        assert "data/2.5/weather" in call_args


@pytest.mark.asyncio
async def test_get_weather_data_api_error(mock_aiohttp_session: AsyncMock) -> None:
    """Test handling API errors when getting weather data."""
    with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
        # Test 404 error
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Not found")

        mock_get = AsyncMock()
        mock_get.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get.__aexit__ = AsyncMock()

        mock_aiohttp_session.__aenter__ = AsyncMock(return_value=mock_aiohttp_session)
        mock_aiohttp_session.__aexit__ = AsyncMock()
        mock_aiohttp_session.get = AsyncMock(return_value=mock_get)

        with pytest.raises(WeatherError, match="Location not found: Invalid Location"):
            await _get_weather_data(
                location="Invalid Location",
                units="metric",
                api_key="test_key"
            )

        # Test 500 error
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal server error")

        mock_get = AsyncMock()
        mock_get.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get.__aexit__ = AsyncMock()

        mock_aiohttp_session.get = AsyncMock(return_value=mock_get)

        with pytest.raises(WeatherError, match="OpenWeatherMap API error: 500 - Internal server error"):
            await _get_weather_data(
                location="London",
                units="metric",
                api_key="test_key"
            )


def test_format_weather_response(mock_weather_response: Dict[str, Any]) -> None:
    """Test formatting weather data into a human-readable string."""
    # Test metric units
    metric_result = _format_weather_response(mock_weather_response, "metric")
    assert "London, GB" in metric_result
    assert "Temperature: 20.0°C" in metric_result
    assert "Feels like: 19.0°C" in metric_result
    assert "Wind speed: 5 m/s" in metric_result
    assert "Humidity: 65%" in metric_result
    assert "Conditions: Clear sky" in metric_result
    
    # Test imperial units
    imperial_data = {
        "name": "New York",
        "sys": {
            "country": "US"
        },
        "weather": [{
            "main": "Rain",
            "description": "light rain"
        }],
        "main": {
            "temp": 68,
            "feels_like": 70,
            "humidity": 80
        },
        "wind": {
            "speed": 10
        }
    }
    
    imperial_result = _format_weather_response(imperial_data, "imperial")
    assert "New York, US" in imperial_result
    assert "Temperature: 68.0°F" in imperial_result
    assert "Feels like: 70.0°F" in imperial_result
    assert "Wind speed: 10 mph" in imperial_result
    assert "Humidity: 80%" in imperial_result
    assert "Conditions: Light rain" in imperial_result


@pytest.mark.asyncio
async def test_weather_handler_success(mock_weather_response: Dict[str, Any], mock_aiohttp_session: AsyncMock) -> None:
    """Test successful weather handler execution."""
    with patch.dict(os.environ, {"OPENWEATHERMAP_API_KEY": "test_key"}):
        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            result = await weather_handler({
                "location": "London",
                "units": "metric"
            })
            
            assert isinstance(result, str)
            assert "London, GB" in result
            assert "Temperature: 20.0°C" in result
            assert "Conditions: Clear sky" in result 