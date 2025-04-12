"""Script to generate test fixtures for weather_server tests.

This script makes real API calls to OpenWeatherMap and saves the responses
as test fixtures that can be used in unit tests.
"""

import json
import os
import requests
from pathlib import Path
from typing import Any, Dict


def save_fixture(name: str, data: Dict[str, Any]) -> None:
    """Save fixture data to a JSON file.

    Args:
        name: Name of the fixture file
        data: Data to save
    """
    fixtures_dir = Path(__file__).parent / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)

    fixture_path = fixtures_dir / f"{name}.json"
    with open(fixture_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved fixture: {fixture_path}")


def generate_weather_fixtures() -> None:
    """Generate test fixtures by making real API calls."""
    api_key = os.environ.get("OPENWEATHERMAP_API_KEY")
    if not api_key:
        raise ValueError("OPENWEATHERMAP_API_KEY environment variable not set")

    # Base URL for OpenWeatherMap API
    base_url = "https://api.openweathermap.org/data/2.5/weather"

    # Test cases and their corresponding fixture names
    test_cases = [
        {
            "name": "london_metric",
            "params": {"q": "London,UK", "units": "metric", "appid": api_key},
        },
        {
            "name": "london_imperial",
            "params": {"q": "London,UK", "units": "imperial", "appid": api_key},
        },
        {
            "name": "nonexistent_city",
            "params": {"q": "NonexistentCity123", "units": "metric", "appid": api_key},
        },
    ]

    for case in test_cases:
        try:
            print(f"\nMaking request for: {case['name']}")
            print(f"Request URL: {base_url}")
            print(f"Parameters: {case['params']}")

            response = requests.get(base_url, params=case["params"])

            # Save both request info and response
            fixture_data = {
                "request": {
                    "url": base_url,
                    "params": {
                        # Save all params except API key
                        k: v
                        for k, v in case["params"].items()
                        if k != "appid"
                    },
                },
                "response": {
                    "status_code": response.status_code,
                    "json": response.json(),
                },
            }

            save_fixture(case["name"], fixture_data)

        except requests.exceptions.RequestException as e:
            print(f"Error making request for {case['name']}: {e}")
            # Save the error response as a fixture too
            fixture_data = {
                "request": {
                    "url": base_url,
                    "params": {k: v for k, v in case["params"].items() if k != "appid"},
                },
                "error": str(e),
            }
            save_fixture(f"{case['name']}_error", fixture_data)


if __name__ == "__main__":
    print("Generating weather API test fixtures...")
    generate_weather_fixtures()
    print("\nDone generating fixtures!")
