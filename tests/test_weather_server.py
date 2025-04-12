"""Unit tests for weather_server.py.

This module provides test coverage for the weather server implementation using real API response fixtures.
"""

import json
import os
import pytest
import aiohttp
from pathlib import Path
from unittest.mock import patch, AsyncMock, Mock

# Mock environment variable before importing the module
with patch.dict(os.environ, {'OPENWEATHERMAP_API_KEY': 'test_api_key'}):
    from server.weather_server import (get_weather, _format_weather_response,
                                       WeatherError, _check_weather_response)


def load_fixture(name: str) -> dict:
    """Load a test fixture from the fixtures directory.

    Args:
        name: Name of the fixture file without .json extension

    Returns:
        Dict containing the fixture data
    """
    fixture_path = Path(__file__).parent / "fixtures" / f"{name}.json"
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
async def mock_aiohttp():
    """Mock aiohttp.ClientSession using real API response fixtures."""
    async def get_response(url, **kwargs):
        params = kwargs.get('params', {})

        # Determine which fixture to use based on params
        if params.get('q') == 'London,UK':
            if params.get('units') == 'metric':
                fixture = load_fixture('london_metric')
            else:
                fixture = load_fixture('london_imperial')
            status = 200
            data = fixture['response']['json']
        elif params.get('q') == 'NonexistentCity123':
            status = 404
            data = {"cod": "404", "message": "city not found"}
        elif not params.get('q'):
            status = 400
            data = {"cod": "400", "message": "Invalid location"}
        else:
            status = 404
            data = {"cod": "404", "message": "city not found"}

        response = AsyncMock()
        response.status = status
        response.json.return_value = data
        response.text.return_value = json.dumps(data)
        response.__aenter__.return_value = response
        response.__aexit__.return_value = None
        return response

    # Create mock session
    mock_session = AsyncMock()
    mock_session.get.side_effect = get_response
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    # Create a mock class that returns our configured session
    class MockClientSession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch('aiohttp.ClientSession', MockClientSession):
        yield mock_session


@pytest.mark.asyncio
class TestGetWeather:
    """Test cases for get_weather function using real API response fixtures."""

    async def test_invalid_json_response(self, mock_aiohttp):
        """Test handling of invalid JSON response."""
        async def raise_json_error(*args, **kwargs):
            response = AsyncMock()
            response.status = 200
            response.json.side_effect = ValueError("Invalid JSON")
            response.__aenter__.return_value = response
            response.__aexit__.return_value = None
            return response

        mock_aiohttp.get.side_effect = raise_json_error
        result = await get_weather("London,UK", "metric")
        assert "Error getting weather" in result

    async def test_invalid_units(self, mock_aiohttp):
        """Test handling of invalid temperature units."""
        result = await get_weather("London,UK", "invalid_unit")
        assert "Invalid units" in result

def test_format_weather_response_success():
    """Test weather response formatting with malformed weather array."""
    data = load_fixture('london_metric')
    response = data['response']['json']
    result = _format_weather_response(response, "metric")
    assert result is not None


def test_format_weather_response_missing_weather():
    """Test weather response formatting with empty data."""
    data = load_fixture('london_metric')
    response = data['response']['json']
    del response['weather']
    with pytest.raises(WeatherError):
        _format_weather_response(response, "metric")

async def test_check_weather_response_404():
    """Test weather response checking with valid data."""
    data = load_fixture('nonexistent_city')
    mock_response = Mock(spec=aiohttp.ClientResponse)
    mock_response.status = 404
    mock_response.json = AsyncMock(return_value=data['response']['json'])
    mock_location = "test_location"
    with pytest.raises(WeatherError, match=f"Location not found: {mock_location}"):
        await  _check_weather_response(mock_response, mock_location)

async def test_check_weather_response_500():
    """Test weather response checking with valid data."""
    data = load_fixture('nonexistent_city')
    mock_response = Mock(spec=aiohttp.ClientResponse)
    mock_response.status = 500
    mock_error_message = "Internal Server Error"
    mock_response.text.return_value = mock_error_message
    mock_response.json = AsyncMock(return_value=data['response']['json'])
    mock_location = "test_location"
    with pytest.raises(WeatherError, match= f"OpenWeatherMap API error: 500 - {mock_error_message}"):
        await  _check_weather_response(mock_response, mock_location)
