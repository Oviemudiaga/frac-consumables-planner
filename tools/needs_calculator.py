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


def calculate_needs(crew_data, crew_id: str = "A") -> dict:
    """
    Count pumps needing replacement for each consumable.

    Args:
        crew_data: CrewData containing all crew information
        crew_id: ID of crew to analyze (default "A")

    Returns:
        Dict mapping consumable name to {pumps_needing: int, total_needed: int}
    """
    # TODO: Implement needs calculation logic
    pass
