"""
Weather checking tool for the Transfer Coordinator Agent.

This tool retrieves weather conditions for crew locations and calculates
travel time multipliers based on current weather.

Usage:
    from tools.weather_checker import check_weather, get_route_weather

    weather_data = check_weather(crew_data)
    route_weather = get_route_weather(crew_data, from_crew="A", to_crew="B")
"""

from langchain_core.tools import tool

from schemas.crew import CrewData
from schemas.weather import WeatherCondition, WeatherData, CrewWeather, WEATHER_MULTIPLIERS
from generator.weather_generator import generate_crew_weather, get_weather_summary


@tool
def check_weather(crew_data: CrewData, seed: int | None = None) -> dict:
    """
    Check weather conditions for all crew locations.

    Returns weather data with travel time multipliers for each crew.
    Weather affects how long transfers will take between crews.

    Args:
        crew_data: CrewData containing all crews
        seed: Optional random seed for reproducible weather (for testing)

    Returns:
        Dictionary with weather data per crew including condition and multiplier
    """
    crew_weather = generate_crew_weather(crew_data, seed=seed)

    result = {
        "crews": [],
        "summary": get_weather_summary(crew_weather)
    }

    for crew_id, cw in crew_weather.items():
        w = cw.weather
        result["crews"].append({
            "crew_id": crew_id,
            "area": cw.area,
            "condition": w.condition.value,
            "temperature_f": w.temperature_f,
            "wind_mph": w.wind_mph,
            "visibility_miles": w.visibility_miles,
            "time_multiplier": w.time_multiplier,
        })

    return result


@tool
def get_route_weather(
    crew_data: CrewData,
    from_crew: str,
    to_crew: str,
    weather_data: dict | None = None,
    seed: int | None = None
) -> dict:
    """
    Get weather conditions for a specific route between two crews.

    Calculates the effective weather multiplier for travel between crews
    by averaging the conditions at origin and destination.

    Args:
        crew_data: CrewData containing all crews
        from_crew: Origin crew ID
        to_crew: Destination crew ID
        weather_data: Pre-fetched weather data (optional, will generate if not provided)
        seed: Optional random seed for reproducible weather

    Returns:
        Dictionary with route weather details including effective multiplier
    """
    # Get weather data if not provided
    if weather_data is None:
        weather_data = check_weather.invoke({"crew_data": crew_data, "seed": seed})

    # Find weather for both crews
    from_weather = None
    to_weather = None

    for crew in weather_data["crews"]:
        if crew["crew_id"] == from_crew:
            from_weather = crew
        elif crew["crew_id"] == to_crew:
            to_weather = crew

    if from_weather is None or to_weather is None:
        return {
            "error": f"Could not find weather for crews {from_crew} and/or {to_crew}",
            "from_crew": from_crew,
            "to_crew": to_crew,
        }

    # Calculate effective multiplier (average of both locations)
    effective_multiplier = (from_weather["time_multiplier"] + to_weather["time_multiplier"]) / 2

    # Determine worst condition for warnings
    from_mult = from_weather["time_multiplier"]
    to_mult = to_weather["time_multiplier"]
    worst_condition = from_weather["condition"] if from_mult >= to_mult else to_weather["condition"]
    worst_location = from_crew if from_mult >= to_mult else to_crew

    # Generate warnings for hazardous conditions
    warnings = []
    if from_mult >= 1.6:
        warnings.append(f"Hazardous conditions at Crew {from_crew}: {from_weather['condition']}")
    if to_mult >= 1.6:
        warnings.append(f"Hazardous conditions at Crew {to_crew}: {to_weather['condition']}")

    return {
        "from_crew": from_crew,
        "to_crew": to_crew,
        "from_weather": from_weather,
        "to_weather": to_weather,
        "effective_multiplier": round(effective_multiplier, 2),
        "worst_condition": worst_condition,
        "worst_location": worst_location,
        "warnings": warnings,
    }


def get_weather_for_crews(crew_data: CrewData, seed: int | None = None) -> dict[str, CrewWeather]:
    """
    Get weather data as CrewWeather objects (non-tool version for internal use).

    Args:
        crew_data: CrewData containing all crews
        seed: Optional random seed for reproducible weather

    Returns:
        Dictionary mapping crew_id to CrewWeather objects
    """
    return generate_crew_weather(crew_data, seed=seed)
