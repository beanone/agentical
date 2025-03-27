"""Weather Tool for Agentical Framework.

This module provides a tool for fetching weather information.

Public Interface:
    - create_weather_tool(): Create the weather tool definition
    - weather_handler(): Handle weather tool calls
    - collect_input(): Collect user input for weather parameters

Examples:
    Basic usage:
    >>> params = {"location": "London", "unit": "celsius"}
    >>> result = await weather_handler(params)
    >>> print(result)
    Weather in London:
    • Conditions: Cloudy
    • Temperature: 15°C
    • Feels like: 14°C
    • Humidity: 75%
    • Wind speed: 4.2 m/s
    
    With country code:
    >>> params = {"location": "London", "country_code": "CA", "unit": "fahrenheit"}
    >>> result = await weather_handler(params)
    >>> print(result)  # Shows weather for London, Canada
"""

import os
from enum import Enum
import aiohttp
from dataclasses import dataclass
from typing import Dict, Any, Optional, Final, List
from datetime import datetime

# Import from my_assistant.mcp.tools.py module
from agentical.core.types import Tool, ToolParameter


# Constants
BASE_URL: Final[str] = "https://api.openweathermap.org/data/2.5/weather"


class TemperatureUnit(str, Enum):
    """Valid temperature units."""
    CELSIUS = "celsius"
    FAHRENHEIT = "fahrenheit"
    KELVIN = "kelvin"


# OpenWeatherMap API mappings
UNIT_MAPPING: Final[Dict[TemperatureUnit, str]] = {
    TemperatureUnit.CELSIUS: "metric",
    TemperatureUnit.FAHRENHEIT: "imperial",
    TemperatureUnit.KELVIN: ""  # Kelvin is the default unit in OpenWeatherMap
}

UNIT_SYMBOLS: Final[Dict[TemperatureUnit, str]] = {
    TemperatureUnit.CELSIUS: "°C",
    TemperatureUnit.FAHRENHEIT: "°F",
    TemperatureUnit.KELVIN: "K"
}


@dataclass(frozen=True)
class WeatherData:
    """Structured weather data.
    
    Attributes:
        description: Weather condition description
        temperature: Current temperature in the specified unit
        feels_like: "Feels like" temperature in the specified unit
        humidity: Relative humidity percentage
        wind_speed: Wind speed in meters per second
    """
    description: str
    temperature: float
    feels_like: float
    humidity: int
    wind_speed: float


class WeatherError(Exception):
    """Raised when there is an error getting weather information."""
    pass


async def collect_input() -> Dict[str, Any]:
    """Collect input parameters from user.
    
    Returns:
        Dictionary of parameters for the weather tool
        
    Raises:
        WeatherError: If input validation fails
    """
    # Get location
    location = input("Enter location (e.g., 'London' or 'New York, US'): ").strip()
    if not location:
        raise WeatherError("Location cannot be empty")
        
    # Get units
    units = input("Enter units (metric/imperial) [metric]: ").strip().lower()
    if not units:
        units = "metric"
    elif units not in ["metric", "imperial"]:
        raise WeatherError("Units must be either 'metric' or 'imperial'")
        
    return {
        "location": location,
        "units": units
    }


def create_weather_tool() -> Tool:
    """Create a weather tool definition.
    
    Returns:
        Tool definition for getting weather information
    """
    return Tool(
        name="get_weather",
        description="Get current weather information for a location",
        parameters={
            "location": ToolParameter(
                type="string",
                description="City name or location (e.g., 'London' or 'New York, US')",
                required=True
            ),
            "units": ToolParameter(
                type="string",
                description="Temperature units (metric = Celsius, imperial = Fahrenheit)",
                required=False,
                default="metric",
                enum=["metric", "imperial"]
            )
        }
    )


async def _check_weather_response(response: aiohttp.ClientResponse, location: str) -> None:
    """Check the weather API response for errors.
    
    Args:
        response: The aiohttp response to check
        location: The location string used in the request, for error messages
        
    Raises:
        WeatherError: If the response indicates an error
    """
    if response.status == 404:
        raise WeatherError(f"Location not found: {location}")
    elif response.status != 200:
        raise WeatherError(
            f"OpenWeatherMap API error: {response.status} - {await response.text()}"
        )


async def _get_weather_data(
    location: str,
    units: str,
    api_key: str
) -> Dict[str, Any]:
    """Get weather data from OpenWeatherMap API.
    
    Args:
        location: City name or location
        units: Temperature units (metric/imperial)
        api_key: OpenWeatherMap API key
        
    Returns:
        Weather data from API
        
    Raises:
        WeatherError: If there is an error getting weather data
        aiohttp.ClientError: If there is a network error
    """
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": location,
        "units": units,
        "appid": api_key
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, params=params) as response:
            await _check_weather_response(response, location)
            return await response.json()


def _format_weather_response(data: Dict[str, Any], units: str) -> str:
    """Format weather data into a human-readable response.
    
    Args:
        data: Weather data from API
        units: Temperature units used (metric/imperial)
        
    Returns:
        Formatted weather information
    """
    # Extract data
    temp = data["main"]["temp"]
    feels_like = data["main"]["feels_like"]
    humidity = data["main"]["humidity"]
    wind_speed = data["wind"]["speed"]
    description = data["weather"][0]["description"]
    
    # Get unit symbols
    temp_unit = "°C" if units == "metric" else "°F"
    speed_unit = "m/s" if units == "metric" else "mph"
    
    # Format response
    return (
        f"Current weather in {data['name']}, {data['sys']['country']}:\n"
        f"Temperature: {temp:.1f}{temp_unit}\n"
        f"Feels like: {feels_like:.1f}{temp_unit}\n"
        f"Humidity: {humidity}%\n"
        f"Wind speed: {wind_speed} {speed_unit}\n"
        f"Conditions: {description.capitalize()}"
    )


async def weather_handler(params: Dict[str, Any]) -> str:
    """Handle weather tool execution.
    
    Args:
        params: Dictionary containing:
            - location: City name or location
            - units: Temperature units (metric/imperial)
            
    Returns:
        Formatted weather information
        
    Raises:
        WeatherError: If there is an error getting weather information
    """
    # Get API key
    api_key = os.environ.get("OPENWEATHERMAP_API_KEY")
    if not api_key:
        raise WeatherError(
            "OpenWeatherMap API key not found. "
            "Please set the OPENWEATHERMAP_API_KEY environment variable."
        )
        
    # Get parameters
    location = params.get("location")
    if not location:
        raise WeatherError("Location parameter is required")
        
    units = params.get("units", "metric")
    if units not in ["metric", "imperial"]:
        raise WeatherError("Units must be either 'metric' or 'imperial'")
        
    try:
        # Get weather data
        weather_data = await _get_weather_data(location, units, api_key)
        
        # Format response
        return _format_weather_response(weather_data, units)
        
    except aiohttp.ClientError as e:
        raise WeatherError(f"Error connecting to OpenWeatherMap API: {str(e)}")
    except Exception as e:
        raise WeatherError(f"Error getting weather information: {str(e)}")
