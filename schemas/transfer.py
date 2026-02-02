"""
Pydantic schemas for transfer planning used by the Transfer Coordinator Agent.

This module defines route segments and transfer plans for moving
consumables between crews with weather-adjusted travel times.

Usage:
    from schemas.transfer import RouteSegment, TransferPlan
"""

from pydantic import BaseModel, Field


class RouteSegment(BaseModel):
    """A single segment of a transfer route between two crews."""

    from_crew: str = Field(description="Origin crew ID")
    to_crew: str = Field(description="Destination crew ID")
    distance_miles: float = Field(
        ge=0.0,
        description="Distance in miles"
    )
    base_travel_time_hours: float = Field(
        ge=0.0,
        description="Base travel time without weather adjustment (distance / avg_speed)"
    )
    weather_condition: str = Field(
        description="Weather condition at destination"
    )
    weather_multiplier: float = Field(
        ge=1.0,
        le=3.0,
        description="Travel time multiplier due to weather"
    )
    adjusted_travel_time_hours: float = Field(
        ge=0.0,
        description="Travel time with weather adjustment applied"
    )
    items_to_pickup: dict[str, int] = Field(
        default_factory=dict,
        description="Items to pick up at destination: {consumable: quantity}"
    )


class TransferPlan(BaseModel):
    """Complete transfer plan with route segments and timing."""

    crew_id: str = Field(description="Destination crew (crew receiving items)")
    segments: list[RouteSegment] = Field(
        default_factory=list,
        description="Ordered list of route segments"
    )
    total_distance_miles: float = Field(
        ge=0.0,
        description="Total distance for entire route"
    )
    total_base_time_hours: float = Field(
        ge=0.0,
        description="Total base travel time without weather"
    )
    total_adjusted_time_hours: float = Field(
        ge=0.0,
        description="Total travel time with weather adjustments"
    )
    weather_delay_hours: float = Field(
        ge=0.0,
        description="Additional time due to weather conditions"
    )
    pickup_manifest: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="Items to pick up by crew: {crew_id: {consumable: quantity}}"
    )

    @property
    def total_time_minutes(self) -> float:
        """Get total adjusted travel time in minutes."""
        return self.total_adjusted_time_hours * 60

    @property
    def weather_delay_minutes(self) -> float:
        """Get weather delay in minutes."""
        return self.weather_delay_hours * 60


# Note: Coordinates class is defined in schemas/crew.py
# Import it from there: from schemas.crew import Coordinates
