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
    _format_weather_response,
    _check_weather_response
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
async def test_check_weather_response() -> None:
    """Test the _check_weather_response function for different response statuses."""
    # Test successful response (200)
    mock_200 = AsyncMock()
    mock_200.status = 200
    await _check_weather_response(mock_200, "London")  # Should not raise

    # Test not found response (404)
    mock_404 = AsyncMock()
    mock_404.status = 404
    with pytest.raises(WeatherError, match="Location not found: Paris"):
        await _check_weather_response(mock_404, "Paris")

    # Test server error response (500)
    mock_500 = AsyncMock()
    mock_500.status = 500
    mock_500.text = AsyncMock(return_value="Internal Server Error")
    with pytest.raises(WeatherError, match="OpenWeatherMap API error: 500 - Internal Server Error"):
        await _check_weather_response(mock_500, "London")

    # Test other error response (403)
    mock_403 = AsyncMock()
    mock_403.status = 403
    mock_403.text = AsyncMock(return_value="Forbidden")
    with pytest.raises(WeatherError, match="OpenWeatherMap API error: 403 - Forbidden"):
        await _check_weather_response(mock_403, "London")


@pytest.mark.asyncio
async def test_get_weather_data_success(mock_weather_response: Dict[str, Any]) -> None:
    """Test successful weather data retrieval."""
    # Set up mock response
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value=mock_weather_response)
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)

    # Set up mock session
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.get = MagicMock(return_value=mock_response)  # Not async - returns context manager directly

    # Mock _check_weather_response
    with patch("examples.tools.weather_tool._check_weather_response") as mock_check:
        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await _get_weather_data(
                location="London",
                units="metric",
                api_key="test_key"
            )
            
            # Verify result
            assert result == mock_weather_response
            
            # Verify API call
            mock_session.get.assert_called_once()
            call_args = mock_session.get.call_args
            assert call_args[0][0] == "http://api.openweathermap.org/data/2.5/weather"
            assert call_args[1]["params"] == {
                "q": "London",
                "units": "metric",
                "appid": "test_key"
            }
            
            # Verify _check_weather_response was called with the response from __aenter__
            mock_check.assert_called_once_with(mock_response, "London")


@pytest.mark.asyncio
async def test_get_weather_data_errors() -> None:
    """Test weather data retrieval with different error responses."""
    test_cases = [
        {
            "status": 404,
            "error": WeatherError("Location not found: NonexistentCity"),
            "location": "NonexistentCity"
        },
        {
            "status": 500,
            "error": WeatherError("OpenWeatherMap API error: 500 - Internal Server Error"),
            "location": "London"
        },
        {
            "status": 403,
            "error": WeatherError("OpenWeatherMap API error: 403 - Invalid API key"),
            "location": "London"
        }
    ]

    for case in test_cases:
        # Set up mock response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={})  # Should not be called
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)

        # Set up mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.get = MagicMock(return_value=mock_response)

        # Mock _check_weather_response to raise the error
        with patch("examples.tools.weather_tool._check_weather_response") as mock_check:
            mock_check.side_effect = case["error"]
            
            with patch("aiohttp.ClientSession", return_value=mock_session):
                with pytest.raises(WeatherError) as exc_info:
                    await _get_weather_data(
                        location=case["location"],
                        units="metric",
                        api_key="test_key"
                    )
                
                assert str(exc_info.value) == str(case["error"])

                # Verify API call was made with correct parameters
                mock_session.get.assert_called_once()
                call_args = mock_session.get.call_args
                assert call_args[0][0] == "http://api.openweathermap.org/data/2.5/weather"
                assert call_args[1]["params"] == {
                    "q": case["location"],
                    "units": "metric",
                    "appid": "test_key"
                }
                
                # Verify _check_weather_response was called with the response from __aenter__
                mock_check.assert_called_once_with(mock_response, case["location"])


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
async def test_check_weather_response() -> None:
    """Test the _check_weather_response function directly."""
    # Test successful response
    mock_success = AsyncMock()
    mock_success.status = 200
    await _check_weather_response(mock_success, "London")  # Should not raise

    # Test 404 response
    mock_404 = AsyncMock()
    mock_404.status = 404
    with pytest.raises(WeatherError, match="Location not found: Test City"):
        await _check_weather_response(mock_404, "Test City")

    # Test other error response
    mock_500 = AsyncMock()
    mock_500.status = 500
    mock_500.text = AsyncMock(return_value="Server Error")
    with pytest.raises(WeatherError, match="OpenWeatherMap API error: 500 - Server Error"):
        await _check_weather_response(mock_500, "Test City") 