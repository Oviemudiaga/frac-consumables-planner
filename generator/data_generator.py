"""
Generate random crew data based on SimulationConfig.

This module provides functions to create randomized crew data for
testing and simulation purposes:
- generate_crew_data(): Create random crews based on config parameters
- load_crew_data(): Load crew data from JSON file
- save_crew_data(): Save crew data to JSON file

The generator respects all SimulationConfig parameters including:
- Number of crews and pumps per crew
- Ranges for job duration, remaining life, and spares
- Distance constraints from Crew A
- Optional seed for reproducibility

Usage:
    from generator.data_generator import generate_crew_data
    from schemas.config import SimulationConfig

    config = SimulationConfig(num_crews=5, seed=42)
    crew_data = generate_crew_data(config)
"""

import json
import random
from pathlib import Path

from schemas.config import SimulationConfig
from schemas.crew import CrewData, Crew, Pump, Spares


# Geographic hierarchy data: Country > Region > Area
GEOGRAPHY_DATA = {
    "United States": {
        "Texas": ["Permian Basin", "Eagle Ford", "Barnett Shale"],
        "North Dakota": ["Bakken", "Three Forks"],
        "Oklahoma": ["SCOOP", "STACK", "Anadarko Basin"],
        "New Mexico": ["Delaware Basin", "San Juan Basin"],
        "Colorado": ["DJ Basin", "Piceance Basin"],
    },
    "Canada": {
        "Alberta": ["Montney", "Duvernay", "Cardium"],
        "British Columbia": ["Horn River", "Liard Basin"],
        "Saskatchewan": ["Bakken", "Viking"],
    }
}


def get_random_geography() -> tuple[str, str, str]:
    """
    Get a random geographic location (country, region, area).

    Returns:
        Tuple of (country, region, area)
    """
    country = random.choice(list(GEOGRAPHY_DATA.keys()))
    region = random.choice(list(GEOGRAPHY_DATA[country].keys()))
    area = random.choice(GEOGRAPHY_DATA[country][region])
    return country, region, area


def generate_crew_data(config: SimulationConfig) -> CrewData:
    """
    Generate randomized crew data based on configuration.

    Args:
        config: SimulationConfig with all parameters

    Returns:
        CrewData with N crews, each with M pumps
    """
    if config.seed is not None:
        random.seed(config.seed)

    crews: list[Crew] = []
    crew_letters = "ABCDEFGHIJ"

    for i in range(config.num_crews):
        crew_id = crew_letters[i]

        # Generate pumps for this crew
        num_pumps = random.randint(config.min_pumps_per_crew, config.max_pumps_per_crew)
        pumps: list[Pump] = []

        for pump_id in range(1, num_pumps + 1):
            pump = Pump(
                pump_id=pump_id,
                valve_packings_life=random.randint(config.min_remaining_life, config.max_remaining_life),
                seals_life=random.randint(config.min_remaining_life, config.max_remaining_life),
                plungers_life=random.randint(config.min_remaining_life, config.max_remaining_life)
            )
            pumps.append(pump)

        # Generate spares
        spares = Spares(
            valve_packings=random.randint(config.min_spares, config.max_spares),
            seals=random.randint(config.min_spares, config.max_spares),
            plungers=random.randint(config.min_spares, config.max_spares)
        )

        # Distance: None for Crew A, random for others
        if i == 0:
            distance = None
        else:
            distance = round(random.uniform(config.min_distance, config.max_distance), 1)

        # Job duration
        job_duration = random.randint(config.min_job_duration, config.max_job_duration)

        # Geographic location
        country, region, area = get_random_geography()

        crew = Crew(
            crew_id=crew_id,
            job_duration_hours=job_duration,
            distance_to_crew_a=distance,
            pumps=pumps,
            spares=spares,
            country=country,
            region=region,
            area=area
        )
        crews.append(crew)

    return CrewData(
        crews=crews,
        proximity_threshold_miles=config.proximity_threshold_miles,
        consumables_per_pump=config.consumables_per_pump
    )


def load_crew_data(filepath: str) -> CrewData:
    """
    Load crew data from JSON file.

    Args:
        filepath: Path to JSON file

    Returns:
        CrewData instance
    """
    path = Path(filepath)
    with open(path, "r") as f:
        data = json.load(f)

    # Remove _description field if present (it's metadata)
    if "_description" in data:
        del data["_description"]

    return CrewData(**data)


def save_crew_data(crew_data: CrewData, filepath: str) -> None:
    """
    Save crew data to JSON file.

    Args:
        crew_data: CrewData instance to save
        filepath: Path to output JSON file
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(crew_data.model_dump(), f, indent=2)
