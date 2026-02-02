"""
Pydantic schemas for weather data used by the Transfer Coordinator Agent.

This module defines weather conditions and their impact on travel times.
Weather data affects route planning and cost calculations.

Usage:
    from schemas.weather import WeatherCondition, WeatherData, WEATHER_MULTIPLIERS
"""

from enum import Enum
from pydantic import BaseModel, Field


class WeatherCondition(str, Enum):
    """Weather conditions that affect travel times."""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    STORM = "storm"
    FOG = "fog"


# Weather impact on travel time multipliers
WEATHER_MULTIPLIERS: dict[WeatherCondition, float] = {
    WeatherCondition.CLEAR: 1.0,       # Normal driving
    WeatherCondition.CLOUDY: 1.1,      # Slightly cautious
    WeatherCondition.RAIN: 1.3,        # Slower speeds
    WeatherCondition.HEAVY_RAIN: 1.6,  # Much slower
    WeatherCondition.STORM: 2.0,       # Hazardous conditions
    WeatherCondition.FOG: 1.4,         # Low visibility
}


class WeatherData(BaseModel):
    """Weather data for a crew location."""

    condition: WeatherCondition = Field(
        default=WeatherCondition.CLEAR,
        description="Current weather condition"
    )
    temperature_f: float = Field(
        default=75.0,
        ge=-40.0,
        le=130.0,
        description="Temperature in Fahrenheit"
    )
    wind_mph: float = Field(
        default=10.0,
        ge=0.0,
        le=150.0,
        description="Wind speed in miles per hour"
    )
    visibility_miles: float = Field(
        default=10.0,
        ge=0.0,
        le=20.0,
        description="Visibility in miles"
    )

    @property
    def time_multiplier(self) -> float:
        """Get travel time multiplier based on weather condition."""
        return WEATHER_MULTIPLIERS.get(self.condition, 1.0)


class CrewWeather(BaseModel):
    """Weather data associated with a specific crew."""

    crew_id: str = Field(description="Crew identifier")
    area: str = Field(description="Geographic area name")
    weather: WeatherData = Field(
        default_factory=WeatherData,
        description="Current weather conditions"
    )
