"""
LangChain tool for calculating consumable replacement needs.

This tool analyzes a crew's pumps and determines which consumables
need replacement based on remaining life vs job duration.

For each consumable type (valve_packings, seals, plungers):
- Count pumps where remaining life < job duration
- Calculate total needed = pumps_needing × consumables_per_pump

Usage:
    Agent calls this tool with crew_data to get:
    {
        "valve_packings": {"pumps_needing": 2, "total_needed": 10},
        "seals": {"pumps_needing": 1, "total_needed": 5},
        "plungers": {"pumps_needing": 0, "total_needed": 0}
    }
"""

from schemas.crew import CrewData


def calculate_needs(crew_data: CrewData, crew_id: str = "A") -> dict:
    """
    Count pumps needing replacement for each consumable.

    Args:
        crew_data: CrewData containing all crew information
        crew_id: ID of crew to analyze (default "A")

    Returns:
        Dict mapping consumable name to {pumps_needing: int, total_needed: int}
    """
    # Find the target crew
    crew = None
    for c in crew_data.crews:
        if c.crew_id == crew_id:
            crew = c
            break

    if crew is None:
        raise ValueError(f"Crew {crew_id} not found")

    # Calculate needs for each consumable type
    consumables = ["valve_packings", "seals", "plungers"]
    result = {}

    for consumable in consumables:
        pumps_needing = 0
        for pump in crew.pumps:
            # Get the remaining life for this consumable
            remaining_life = getattr(pump, f"{consumable}_life")
            if remaining_life < crew.job_duration_hours:
                pumps_needing += 1

        total_needed = pumps_needing * crew_data.consumables_per_pump
        result[consumable] = {
            "pumps_needing": pumps_needing,
            "total_needed": total_needed
        }

    return result
