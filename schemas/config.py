"""
Simulation configuration schema.

This module defines SimulationConfig, which contains all configurable
parameters for data generation and simulation:
- Crew configuration (num_crews, pumps_per_crew ranges)
- Thresholds (proximity, consumables_per_pump)
- Generation ranges (job_duration, remaining_life, spares, distance)
- Reproducibility (seed)

Usage:
    from schemas.config import SimulationConfig

    config = SimulationConfig(num_crews=5, seed=42)
"""

from pydantic import BaseModel, Field


class SimulationConfig(BaseModel):
    """Configuration for data generation and simulation."""

    # Crew configuration
    num_crews: int = Field(default=3, ge=2, le=10, description="Number of crews to generate")
    min_pumps_per_crew: int = Field(default=2, ge=1, le=6, description="Minimum pumps per crew")
    max_pumps_per_crew: int = Field(default=5, ge=2, le=8, description="Maximum pumps per crew")

    # Job duration ranges (hours)
    min_job_duration: int = Field(default=40, ge=20, le=80, description="Minimum job duration in hours")
    max_job_duration: int = Field(default=70, ge=40, le=120, description="Maximum job duration in hours")

    # Remaining life ranges (hours)
    min_remaining_life: int = Field(default=30, ge=0, le=100, description="Minimum remaining life for consumables")
    max_remaining_life: int = Field(default=90, ge=50, le=150, description="Maximum remaining life for consumables")

    # Spares ranges
    min_spares: int = Field(default=0, ge=0, le=10, description="Minimum spares per consumable type")
    max_spares: int = Field(default=20, ge=5, le=50, description="Maximum spares per consumable type")

    # Distance ranges (miles)
    min_distance: float = Field(default=1.0, ge=0.5, le=5.0, description="Minimum distance from Crew A")
    max_distance: float = Field(default=15.0, ge=5.0, le=50.0, description="Maximum distance from Crew A")

    # Thresholds
    proximity_threshold_miles: float = Field(default=10.0, ge=5.0, le=50.0, description="Max distance for nearby crews")
    consumables_per_pump: int = Field(default=5, ge=1, le=10, description="Consumables required per pump")

    # Reproducibility
    seed: int | None = Field(default=None, description="Random seed for reproducibility")
