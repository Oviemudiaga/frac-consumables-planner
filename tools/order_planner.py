"""
Tool: Compute borrow vs order quantities.

This tool takes the calculated needs and available inventory,
then determines the optimal borrowing strategy and order quantities.

Input:
  - needs: dict[str, int] (consumable name -> quantity needed)
  - inventory: list[Crew] (inventory data from all crews)
  - crew_id: str (requesting crew's ID, default "A")

Output:
  - OrderPlan containing:
    * Breakdown for each consumable (on-hand, borrow sources, order qty)
    * Total order cost
    * Natural language recommendation

Business Logic:
  1. Check on-hand inventory (remaining_life > job_duration)
  2. Attempt to borrow from nearby crews' surplus
  3. Order remaining deficit
  4. Calculate total cost (mock $100/unit)

Usage:
  Final tool called by agent to generate the complete order plan
  that will be displayed in the Streamlit UI.
"""

from langchain.tools import tool
from schemas.crew import Crew
from schemas.order import OrderPlan


@tool
def plan_order(
    needs: dict[str, int],
    inventory: list[Crew],
    crew_id: str = "A",
    job_duration_hours: int = 200
) -> OrderPlan:
    """
    Generate order plan with borrow strategy.

    Args:
        needs: Dictionary of consumable needs
        inventory: List of crew inventory data
        crew_id: Requesting crew's ID
        job_duration_hours: Job duration for life validation

    Returns:
        OrderPlan with line items, costs, and recommendation
    """
    # Implementation will be added in Phase 4
    ...
