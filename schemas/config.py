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

    # TODO: Implement fields with validation
    pass
