"""Weather Tool for Agentical Framework.

This module provides an MCP-compliant tool for fetching weather information.

Examples:
    Basic usage:
    >>> result = await get_weather("London", "metric")
    >>> print(result)
    Weather in London:
    • Conditions: Cloudy
    • Temperature: 15°C
    • Feels like: 14°C
    • Humidity: 75%
    • Wind speed: 4.2 m/s
    
    With country code:
    >>> result = await get_weather("London, CA", "imperial")
    >>> print(result)  # Shows weather for London, Canada
"""

import os
from enum import Enum
import aiohttp
from dataclasses import dataclass
from typing import Dict, Any, Final
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather")

# Constants
BASE_URL: Final[str] = "http://api.openweathermap.org/data/2.5/weather"
API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

if not API_KEY:
    raise ValueError("OPENWEATHERMAP_API_KEY environment variable is required")

class WeatherError(Exception):
    """Raised when there is an error getting weather information."""
    pass

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


async def _get_weather_data(location: str, units: str = "metric") -> Dict[str, Any]:
    """Get weather data from OpenWeatherMap API.
    
    Args:
        location: City name or location
        units: Temperature units (metric/imperial)
        
    Returns:
        Weather data from API
        
    Raises:
        WeatherError: If there is an error getting weather data
        aiohttp.ClientError: If there is a network error
    """
    params = {
        "q": location,
        "units": units,
        "appid": API_KEY
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(BASE_URL, params=params) as response:
                await _check_weather_response(response, location)
                return await response.json()
    except aiohttp.ClientError as e:
        raise WeatherError(f"Network error: {str(e)}")


def _format_weather_response(data: Dict[str, Any], units: str) -> str:
    """Format weather data into a human-readable response.
    
    Args:
        data: Weather data from API
        units: Temperature units used (metric/imperial)
        
    Returns:
        Formatted weather information
    """
    try:
        weather = data["weather"][0]
        main = data["main"]
        wind = data["wind"]
        
        # Get temperature symbol
        temp_symbol = "°C" if units == "metric" else "°F"
        
        # Format response
        lines = [
            f"Weather in {data['name']}, {data['sys']['country']}:",
            f"• Conditions: {weather['description'].capitalize()}",
            f"• Temperature: {main['temp']:.1f}{temp_symbol}",
            f"• Feels like: {main['feels_like']:.1f}{temp_symbol}",
            f"• Humidity: {main['humidity']}%",
            f"• Wind speed: {wind['speed']:.1f} {'m/s' if units == 'metric' else 'mph'}"
        ]
        
        return "\n".join(lines)
    except KeyError as e:
        raise WeatherError(f"Invalid weather data format: missing {str(e)}")


@mcp.tool()
async def get_weather(location: str, units: str = "metric") -> str:
    """Get current weather information for a location.
    
    Args:
        location: City name or location (e.g., 'London' or 'New York, US')
        units: Temperature units ('metric' for Celsius, 'imperial' for Fahrenheit)
        
    Returns:
        Formatted weather information as a string
        
    Example:
        >>> await get_weather("London", "metric")
        Weather in London, GB:
        • Conditions: Cloudy
        • Temperature: 15.0°C
        • Feels like: 14.2°C
        • Humidity: 75%
        • Wind speed: 4.2 m/s
    """
    try:
        if units not in ["metric", "imperial"]:
            return f"Invalid units: {units}. Must be 'metric' or 'imperial'."
            
        data = await _get_weather_data(location, units)
        return _format_weather_response(data, units)
    except WeatherError as e:
        return str(e)
    except Exception as e:
        return f"Error getting weather: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport='stdio')
