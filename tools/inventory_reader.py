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

from schemas.crew import CrewData, Spares
from tools.needs_calculator import calculate_needs


def read_inventory(crew_data: CrewData) -> dict:
    """
    Read all crews, compute available spares for nearby crews.

    Args:
        crew_data: CrewData containing all crew information

    Returns:
        Dict with crew_a_spares and nearby_crews list (sorted by distance)
    """
    # Find Crew A (distance_to_crew_a is None)
    crew_a = None
    for crew in crew_data.crews:
        if crew.distance_to_crew_a is None:
            crew_a = crew
            break

    if crew_a is None:
        raise ValueError("Crew A not found")

    # Process nearby crews
    nearby_crews = []
    for crew in crew_data.crews:
        # Skip Crew A itself
        if crew.distance_to_crew_a is None:
            continue

        # Only include crews within proximity threshold
        if crew.distance_to_crew_a > crew_data.proximity_threshold_miles:
            continue

        # Calculate this crew's needs
        needs = calculate_needs(crew_data, crew.crew_id)

        # Calculate available spares (their_spares - their_needs)
        available = {}
        for consumable in ["valve_packings", "seals", "plungers"]:
            on_hand = getattr(crew.spares, consumable)
            needed = needs[consumable]["total_needed"]
            available[consumable] = max(0, on_hand - needed)

        nearby_crews.append({
            "crew_id": crew.crew_id,
            "distance": crew.distance_to_crew_a,
            "available": available
        })

    # Sort by distance (closest first)
    nearby_crews.sort(key=lambda x: x["distance"])

    return {
        "crew_a_spares": crew_a.spares,
        "nearby_crews": nearby_crews
    }
