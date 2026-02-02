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

    # TODO: Implement fields
    pass


class Spares(BaseModel):
    """Spare parts inventory."""

    # TODO: Implement fields
    pass


class Crew(BaseModel):
    """A fracturing crew."""

    # TODO: Implement fields
    pass


class CrewData(BaseModel):
    """Root model for all crew data."""

    # TODO: Implement fields
    pass
