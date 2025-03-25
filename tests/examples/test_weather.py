"""Tests for the weather tool."""

import os
import pytest
from typing import Dict, Any
from unittest.mock import AsyncMock, patch

from examples.tools.weather_tool import (
    WeatherError,
    create_weather_tool,
    weather_handler,
    _get_weather_data,
    _format_weather_response
)


def test_create_weather_tool() -> None:
    """Test creating the weather tool definition."""
    tool = create_weather_tool()
    
    # Verify tool properties
    assert tool.name == "weather"
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
        with pytest.raises(WeatherError, match="Invalid units"):
            await weather_handler({
                "location": "London",
                "units": "invalid"
            })


@pytest.mark.asyncio
async def test_get_weather_data() -> None:
    """Test getting weather data from the API."""
    mock_response = {
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
    
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_get.return_value.__aenter__.return_value.json = AsyncMock(
            return_value=mock_response
        )
        mock_get.return_value.__aenter__.return_value.status = 200
        
        result = await _get_weather_data(
            api_key="test_key",
            location="London",
            units="metric"
        )
        
        assert result == mock_response
        
        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args[0][0]
        assert "London" in call_args
        assert "metric" in call_args
        assert "test_key" in call_args


@pytest.mark.asyncio
async def test_get_weather_data_api_error() -> None:
    """Test handling API errors when getting weather data."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        # Test API error response
        mock_get.return_value.__aenter__.return_value.status = 404
        mock_get.return_value.__aenter__.return_value.text = AsyncMock(
            return_value="Not found"
        )
        
        with pytest.raises(WeatherError, match="API error"):
            await _get_weather_data(
                api_key="test_key",
                location="Invalid Location",
                units="metric"
            )
        
        # Test connection error
        mock_get.side_effect = Exception("Connection error")
        
        with pytest.raises(WeatherError, match="Error fetching weather data"):
            await _get_weather_data(
                api_key="test_key",
                location="London",
                units="metric"
            )


def test_format_weather_response() -> None:
    """Test formatting weather data into a human-readable string."""
    # Test metric units
    metric_data = {
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
    
    metric_result = _format_weather_response(metric_data, "metric")
    assert "20°C" in metric_result
    assert "19°C" in metric_result
    assert "5 m/s" in metric_result
    assert "65%" in metric_result
    assert "Clear" in metric_result
    assert "clear sky" in metric_result
    
    # Test imperial units
    imperial_data = {
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
    assert "68°F" in imperial_result
    assert "70°F" in imperial_result
    assert "10 mph" in imperial_result
    assert "80%" in imperial_result
    assert "Rain" in imperial_result
    assert "light rain" in imperial_result


def test_format_weather_response_missing_data() -> None:
    """Test formatting weather data with missing fields."""
    incomplete_data = {
        "weather": [{
            "main": "Clear"
            # Missing description
        }],
        "main": {
            "temp": 20
            # Missing feels_like and humidity
        }
        # Missing wind
    }
    
    result = _format_weather_response(incomplete_data, "metric")
    assert "20°C" in result
    assert "Clear" in result
    assert "N/A" in result  # For missing data 