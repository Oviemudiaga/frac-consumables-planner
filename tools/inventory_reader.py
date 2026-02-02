"""
LangChain tool for reading crew inventory and computing available spares.

This tool analyzes all crews to determine:
- Crew A's spare parts on hand
- Nearby crews (within proximity threshold) and their available spares

A crew's "available" spares = their spares - their own needs
(A crew won't lend parts they need themselves)

Nearby crews are sorted by distance (closest first) for the borrow algorithm.

Usage:
    Agent calls this tool with crew_data to get:
    {
        "crew_a_spares": Spares(...),
        "nearby_crews": [
            {"crew_id": "B", "distance": 3.5, "available": {...}},
            {"crew_id": "C", "distance": 8.0, "available": {...}}
        ]
    }
"""


def read_inventory(crew_data) -> dict:
    """
    Read all crews, compute available spares for nearby crews.

    Args:
        crew_data: CrewData containing all crew information

    Returns:
        Dict with crew_a_spares and nearby_crews list (sorted by distance)
    """
    # TODO: Implement inventory reading logic
    pass
