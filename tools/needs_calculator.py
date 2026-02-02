"""
Tool: Calculate consumables needed for a job.

This tool calculates the quantity of each consumable type needed
based on the number of pumps and job duration in hours.

Formula:
  quantity_needed = (pumps * hours) / consumables_per_pump

Input:
  - pumps: int (number of pumps)
  - hours: int (job duration in hours)

Output:
  - dict mapping consumable names to quantities needed
    e.g., {"valve_packings": 60, "seals": 60, "valves": 60}

Usage:
  This tool is called first by the agent to determine total needs
  before checking inventory and planning orders.
"""

from langchain.tools import tool


@tool
def calculate_consumables_needed(pumps: int, hours: int) -> dict[str, int]:
    """
    Calculate consumables needed for a frac job.

    Args:
        pumps: Number of pumps for the job
        hours: Duration of job in hours

    Returns:
        Dictionary mapping consumable names to quantities needed
    """
    # Implementation will be added in Phase 4
    ...
