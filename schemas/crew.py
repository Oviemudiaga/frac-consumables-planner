"""
Pydantic models for crew and pump data.

This module defines the core data models:
- Pump: A single pump with remaining life per consumable
- Spares: Spare parts inventory for a crew
- Crew: A fracturing crew with pumps and spares
- CrewData: Root model containing all crews

Usage:
    from schemas.crew import Crew, CrewData, Pump, Spares

    pump = Pump(pump_id=1, valve_packings_life=50, seals_life=60, plungers_life=70)
    spares = Spares(valve_packings=10, seals=5, plungers=3)
    crew = Crew(crew_id="A", job_duration_hours=60, pumps=[pump], spares=spares)
"""

from pydantic import BaseModel, Field


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
    """A fracturing crew."""

    crew_id: str = Field(description="Crew identifier")
    job_duration_hours: int = Field(gt=0, description="Job duration in hours")
    distance_to_crew_a: float | None = Field(default=None, description="Distance to Crew A in miles (null for Crew A itself)")
    pumps: list[Pump] = Field(description="List of pumps in this crew")
    spares: Spares = Field(description="Spare parts inventory")


class CrewData(BaseModel):
    """Root model for all crew data."""

    crews: list[Crew] = Field(description="List of all crews")
    proximity_threshold_miles: float = Field(gt=0, description="Maximum distance for crew to be considered nearby")
    consumables_per_pump: int = Field(gt=0, description="Number of each consumable type required per pump")
