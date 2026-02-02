"""
LangChain tool for planning orders using N-crew borrow logic.

This tool implements the borrow-first-then-order algorithm:
1. Calculate shortfall = total_needed - spares_on_hand
2. If shortfall > 0, apply N-crew borrow logic:
   a. Check if any single nearby crew can fully fulfill → use closest one
   b. If not, accumulate from multiple crews (closest first)
   c. Order whatever remains unfulfilled

The algorithm minimizes orders by maximizing borrowing from nearby crews.

Usage:
    Agent calls this tool with needs, spares, and nearby_crews to get:
    OrderPlan with items showing borrow sources and order quantities
"""


def plan_order(needs: dict, crew_a_spares, nearby_crews: list, consumables_per_pump: int):
    """
    Apply N-crew borrow logic for each consumable.

    Args:
        needs: Dict of consumable needs from needs_calculator
        crew_a_spares: Spares object for Crew A
        nearby_crews: List of nearby crews with available spares
        consumables_per_pump: Number of each consumable per pump

    Returns:
        OrderPlan with complete order details
    """
    # TODO: Implement order planning logic
    pass


def apply_n_crew_borrow_logic(shortfall: int, nearby_crews: list, consumable: str):
    """
    Generalized N-crew borrow algorithm.

    1. Check if any single crew can fully fulfill → use closest one that can
    2. If no single crew can, accumulate from closest to furthest
    3. Order whatever remains

    Args:
        shortfall: Number of consumables needed
        nearby_crews: List of crews sorted by distance (closest first)
        consumable: Name of consumable type

    Returns:
        Tuple of (list[BorrowSource], to_order: int)
    """
    # TODO: Implement N-crew borrow algorithm
    pass
