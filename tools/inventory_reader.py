"""
Tool: Read crew inventory from static data.

This tool reads inventory data for specified crews from data/crews.json
and filters based on proximity threshold.

Input:
  - crew_ids: list[str] (e.g., ["A", "B", "C"])
  - proximity_threshold: float (max distance in miles, default from config)

Output:
  - list[Crew] containing inventory data for crews within proximity

Business Logic:
  - Crew A is always included (self, distance = None)
  - Other crews included if distance <= proximity_threshold
  - Returns inventory with remaining_life and surplus for each consumable

Usage:
  Called by agent after calculating needs to check what's available
  locally and from nearby crews.
"""

from langchain.tools import tool
from schemas.crew import Crew


@tool
def read_crew_inventory(crew_ids: list[str], proximity_threshold: float = 5.0) -> list[Crew]:
    """
    Read inventory data for specified crews.

    Args:
        crew_ids: List of crew IDs to fetch inventory for
        proximity_threshold: Maximum distance in miles for nearby crews

    Returns:
        List of Crew objects with inventory data
    """
    # Implementation will be added in Phase 4
    ...
