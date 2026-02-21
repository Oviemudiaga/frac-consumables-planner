"""
Weather simulation generator for the Transfer Coordinator Agent.

This module generates simulated weather conditions for crew locations.
Can be seeded for reproducibility or set to specific conditions for testing.

Usage:
    from generator.weather_generator import generate_weather, generate_crew_weather

    # Random weather for an area
    weather = generate_weather("Permian Basin")

    # Weather for all crews
    crew_weather = generate_crew_weather(crew_data)
"""

import random
from schemas.weather import WeatherCondition, WeatherData, CrewWeather, WEATHER_MULTIPLIERS
from schemas.crew import CrewData


# Weather probabilities by season/region (simplified)
WEATHER_PROBABILITIES: dict[WeatherCondition, float] = {
    WeatherCondition.CLEAR: 0.45,
    WeatherCondition.CLOUDY: 0.25,
    WeatherCondition.RAIN: 0.15,
    WeatherCondition.HEAVY_RAIN: 0.05,
    WeatherCondition.STORM: 0.03,
    WeatherCondition.FOG: 0.07,
}

# Temperature ranges by condition (Fahrenheit)
TEMP_RANGES: dict[WeatherCondition, tuple[float, float]] = {
    WeatherCondition.CLEAR: (70, 95),
    WeatherCondition.CLOUDY: (60, 85),
    WeatherCondition.RAIN: (55, 75),
    WeatherCondition.HEAVY_RAIN: (50, 70),
    WeatherCondition.STORM: (45, 65),
    WeatherCondition.FOG: (50, 70),
}

# Wind ranges by condition (mph)
WIND_RANGES: dict[WeatherCondition, tuple[float, float]] = {
    WeatherCondition.CLEAR: (0, 15),
    WeatherCondition.CLOUDY: (5, 20),
    WeatherCondition.RAIN: (10, 25),
    WeatherCondition.HEAVY_RAIN: (15, 35),
    WeatherCondition.STORM: (25, 60),
    WeatherCondition.FOG: (0, 10),
}

# Visibility ranges by condition (miles)
VISIBILITY_RANGES: dict[WeatherCondition, tuple[float, float]] = {
    WeatherCondition.CLEAR: (8, 10),
    WeatherCondition.CLOUDY: (6, 10),
    WeatherCondition.RAIN: (3, 7),
    WeatherCondition.HEAVY_RAIN: (1, 4),
    WeatherCondition.STORM: (0.5, 2),
    WeatherCondition.FOG: (0.25, 2),
}


def generate_weather(
    area: str = "Permian Basin",
    seed: int | None = None,
    forced_condition: WeatherCondition | None = None
) -> WeatherData:
    """
    Generate simulated weather for an area.

    Args:
        area: Geographic area name (for future region-specific weather)
        seed: Random seed for reproducibility
        forced_condition: Force a specific weather condition (for testing)

    Returns:
        WeatherData with simulated conditions
    """
    if seed is not None:
        random.seed(seed)

    # Determine condition
    if forced_condition is not None:
        condition = forced_condition
    else:
        conditions = list(WEATHER_PROBABILITIES.keys())
        weights = list(WEATHER_PROBABILITIES.values())
        condition = random.choices(conditions, weights=weights, k=1)[0]

    # Generate temperature, wind, visibility based on condition
    temp_range = TEMP_RANGES[condition]
    wind_range = WIND_RANGES[condition]
    vis_range = VISIBILITY_RANGES[condition]

    temperature_f = round(random.uniform(*temp_range), 1)
    wind_mph = round(random.uniform(*wind_range), 1)
    visibility_miles = round(random.uniform(*vis_range), 1)

    return WeatherData(
        condition=condition,
        temperature_f=temperature_f,
        wind_mph=wind_mph,
        visibility_miles=visibility_miles,
    )


def generate_crew_weather(
    crew_data: CrewData,
    seed: int | None = None,
    forced_conditions: dict[str, WeatherCondition] | None = None
) -> dict[str, CrewWeather]:
    """
    Generate weather for all crews in the data.

    Args:
        crew_data: CrewData containing all crews
        seed: Random seed for reproducibility
        forced_conditions: Dict of crew_id -> WeatherCondition for testing

    Returns:
        Dict of crew_id -> CrewWeather
    """
    if seed is not None:
        random.seed(seed)

    result = {}
    for crew in crew_data.crews:
        crew_id = crew.crew_id
        area = getattr(crew, 'area', 'Permian Basin')

        # Check for forced condition
        forced = None
        if forced_conditions and crew_id in forced_conditions:
            forced = forced_conditions[crew_id]

        weather = generate_weather(area=area, forced_condition=forced)
        result[crew_id] = CrewWeather(
            crew_id=crew_id,
            area=area,
            weather=weather,
        )

    return result


def get_weather_summary(crew_weather: dict[str, CrewWeather]) -> str:
    """
    Generate a human-readable weather summary.

    Args:
        crew_weather: Dict of crew_id -> CrewWeather

    Returns:
        Formatted string summary
    """
    lines = ["Weather Conditions:"]
    for crew_id, cw in sorted(crew_weather.items()):
        w = cw.weather
        multiplier = WEATHER_MULTIPLIERS[w.condition]
        condition_display = w.condition.value.replace("_", " ").title()
        lines.append(
            f"  Crew {crew_id} ({cw.area}): {condition_display} "
            f"({w.temperature_f}°F, {w.wind_mph} mph wind, "
            f"{w.visibility_miles} mi visibility) - {multiplier}x travel time"
        )
    return "\n".join(lines)
