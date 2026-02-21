"""
Pydantic models for crew and pump data.

This module defines the core data models:
- Pump: A single pump with remaining life per consumable
- Spares: Spare parts inventory for a crew
- Crew: A fracturing crew with pumps and spares
- CrewData: Root model containing all crews
- Coordinates: Geographic coordinates for location

Usage:
    from schemas.crew import Crew, CrewData, Pump, Spares, Coordinates

    pump = Pump(pump_id=1, valve_packings_life=50, seals_life=60, plungers_life=70)
    spares = Spares(valve_packings=10, seals=5, plungers=3)
    coords = Coordinates(lat=31.9686, lng=-102.0779)
    crew = Crew(crew_id="A", job_duration_hours=60, pumps=[pump], spares=spares, coordinates=coords)
"""

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    """Geographic coordinates for a location."""

    lat: float = Field(
        ge=-90.0,
        le=90.0,
        description="Latitude"
    )
    lng: float = Field(
        ge=-180.0,
        le=180.0,
        description="Longitude"
    )


class Pump(BaseModel):
    """A single pump with remaining life per consumable."""

    pump_id: int = Field(description="Pump identifier")
    valve_packings_life: int = Field(ge=0, description="Remaining hours for valve packings")
    seals_life: int = Field(ge=0, description="Remaining hours for seals")
    plungers_life: int = Field(ge=0, description="Remaining hours for plungers")


class Spares(BaseModel):
    """Spare parts inventory."""

    valve_packings: int = Field(default=0, ge=0, description="Number of valve packing spares")
    seals: int = Field(default=0, ge=0, description="Number of seal spares")
    plungers: int = Field(default=0, ge=0, description="Number of plunger spares")


class Crew(BaseModel):
    """A fracturing crew with geographic location."""

    crew_id: str = Field(description="Crew identifier")
    job_duration_hours: int = Field(gt=0, description="Job duration in hours")
    distance_to_crew_a: float | None = Field(default=None, description="Distance to Crew A in miles (null for Crew A itself)")
    pumps: list[Pump] = Field(description="List of pumps in this crew")
    spares: Spares = Field(description="Spare parts inventory")
    # Geographic hierarchy: Country > Region > Area
    country: str = Field(default="United States", description="Country where crew is located")
    region: str = Field(default="Texas", description="Region/state within country")
    area: str = Field(default="Permian Basin", description="Specific area/basin within region")
    # Coordinates for route planning
    coordinates: Coordinates | None = Field(
        default=None,
        description="Geographic coordinates for route planning"
    )


class CrewData(BaseModel):
    """Root model for all crew data."""

    crews: list[Crew] = Field(description="List of all crews")
    proximity_threshold_miles: float = Field(gt=0, description="Maximum distance for crew to be considered nearby")
    consumables_per_pump: int = Field(gt=0, description="Number of each consumable type required per pump")
