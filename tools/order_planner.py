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

from schemas.crew import Spares
from schemas.order import BorrowSource, OrderLineItem, OrderPlan


def plan_order(needs: dict, crew_a_spares: Spares, nearby_crews: list, crew_id: str, job_duration_hours: int):
    """
    Apply N-crew borrow logic for each consumable.

    Args:
        needs: Dict of consumable needs from needs_calculator
        crew_a_spares: Spares object for Crew A
        nearby_crews: List of nearby crews with available spares
        crew_id: ID of the crew this plan is for
        job_duration_hours: Job duration in hours

    Returns:
        OrderPlan with complete order details
    """
    items = []

    for consumable in ["valve_packings", "seals", "plungers"]:
        # Get needs for this consumable
        pumps_needing = needs[consumable]["pumps_needing"]
        total_needed = needs[consumable]["total_needed"]

        # Get what we have on hand
        on_hand = getattr(crew_a_spares, consumable)

        # Calculate shortfall
        shortfall = max(0, total_needed - on_hand)

        # Apply N-crew borrow logic if there's a shortfall
        borrow_sources = []
        to_order = 0

        if shortfall > 0:
            borrow_sources, to_order = apply_n_crew_borrow_logic(
                shortfall, nearby_crews, consumable
            )

        # Create order line item
        item = OrderLineItem(
            consumable_name=consumable,
            pumps_needing=pumps_needing,
            total_needed=total_needed,
            on_hand=on_hand,
            borrow_sources=borrow_sources,
            to_order=to_order
        )
        items.append(item)

    # Create and return the order plan
    return OrderPlan(
        crew_id=crew_id,
        job_duration_hours=job_duration_hours,
        items=items
    )


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
    # Step 1: Check if any single crew can fully fulfill
    for crew in nearby_crews:
        available = crew["available"][consumable]
        if available >= shortfall:
            # This crew can fully fulfill the shortfall
            borrow_source = BorrowSource(
                crew_id=crew["crew_id"],
                quantity=shortfall,
                distance=crew["distance"]
            )
            return ([borrow_source], 0)

    # Step 2: Accumulate from multiple crews (closest first)
    remaining = shortfall
    borrows = []
    for crew in nearby_crews:
        available = crew["available"][consumable]
        if available > 0 and remaining > 0:
            borrow_qty = min(available, remaining)
            borrow_source = BorrowSource(
                crew_id=crew["crew_id"],
                quantity=borrow_qty,
                distance=crew["distance"]
            )
            borrows.append(borrow_source)
            remaining -= borrow_qty

    # Step 3: Order whatever remains
    return (borrows, remaining)
