"""
LangChain tool for planning orders using cost-optimized borrow logic.

This tool implements a cost-optimized borrow-vs-order algorithm:
1. Calculate shortfall = total_needed - spares_on_hand
2. If shortfall > 0, compare borrow cost per unit vs order cost per unit:
   a. For each nearby crew, calculate weather-adjusted borrow cost per unit
   b. Calculate order cost per unit (parts + amortized shipping)
   c. Borrow from crews where borrow is cheaper, order the rest
3. Falls back to proximity-first logic if no weather/cost data provided

Usage:
    Agent calls this tool with needs, spares, and nearby_crews to get:
    OrderPlan with items showing borrow sources and order quantities
"""

from schemas.crew import Spares
from schemas.cost import CostConfig
from schemas.order import BorrowSource, OrderLineItem, OrderPlan
from tools.cost_calculator import load_cost_config


def plan_order(
    needs: dict,
    crew_a_spares: Spares,
    nearby_crews: list,
    crew_id: str,
    job_duration_hours: int,
    weather_data: dict | None = None,
    cost_config: CostConfig | None = None,
) -> OrderPlan:
    """
    Plan consumable orders using cost-optimized borrow logic.

    When weather_data and cost_config are provided, uses cost-per-unit
    comparison to decide borrow vs order. Otherwise falls back to
    proximity-first logic.

    Args:
        needs: Dict of consumable needs from needs_calculator
        crew_a_spares: Spares object for Crew A
        nearby_crews: List of nearby crews with available spares
        crew_id: ID of the crew this plan is for
        job_duration_hours: Job duration in hours
        weather_data: Weather data from check_weather (optional)
        cost_config: CostConfig with pricing info (optional)

    Returns:
        OrderPlan with complete order details
    """
    use_cost_optimization = weather_data is not None and cost_config is not None

    # Calculate total shortfall across all consumables (for amortizing shipping)
    total_shortfall_all = 0
    if use_cost_optimization:
        for consumable in ["valve_packings", "seals", "plungers"]:
            total_needed = needs[consumable]["total_needed"]
            on_hand = getattr(crew_a_spares, consumable)
            total_shortfall_all += max(0, total_needed - on_hand)

    items = []

    for consumable in ["valve_packings", "seals", "plungers"]:
        pumps_needing = needs[consumable]["pumps_needing"]
        total_needed = needs[consumable]["total_needed"]
        on_hand = getattr(crew_a_spares, consumable)
        shortfall = max(0, total_needed - on_hand)

        borrow_sources = []
        to_order = 0

        if shortfall > 0:
            if use_cost_optimization:
                borrow_sources, to_order = _apply_cost_optimized_logic(
                    shortfall, nearby_crews, consumable,
                    weather_data, cost_config, total_shortfall_all
                )
            else:
                borrow_sources, to_order = _apply_proximity_logic(
                    shortfall, nearby_crews, consumable
                )

        item = OrderLineItem(
            consumable_name=consumable,
            pumps_needing=pumps_needing,
            total_needed=total_needed,
            on_hand=on_hand,
            borrow_sources=borrow_sources,
            to_order=to_order
        )
        items.append(item)

    return OrderPlan(
        crew_id=crew_id,
        job_duration_hours=job_duration_hours,
        items=items
    )


def _calculate_borrow_cost_per_unit(
    distance: float,
    quantity: int,
    weather_multiplier: float,
    cost_config: CostConfig,
) -> float:
    """
    Calculate the cost per unit of borrowing from a specific crew.

    Args:
        distance: One-way distance to crew in miles
        quantity: Number of units available to borrow
        weather_multiplier: Weather time multiplier for this route
        cost_config: Cost configuration

    Returns:
        Cost per unit in dollars
    """
    round_trip = distance * 2
    travel_cost = round_trip * cost_config.travel.cost_per_mile
    travel_time = round_trip / cost_config.travel.average_speed_mph
    labor_cost = travel_time * weather_multiplier * cost_config.travel.cost_per_hour_labor
    total_trip_cost = travel_cost + labor_cost
    return total_trip_cost / quantity if quantity > 0 else float("inf")


def _calculate_order_cost_per_unit(
    consumable: str,
    total_shortfall_all: int,
    cost_config: CostConfig,
) -> float:
    """
    Calculate the cost per unit of ordering from supplier.

    Shipping is amortized across all ordered units.

    Args:
        consumable: Consumable name
        total_shortfall_all: Total shortfall across all consumables (for shipping amortization)
        cost_config: Cost configuration

    Returns:
        Cost per unit in dollars
    """
    unit_price = cost_config.consumables[consumable].unit_price
    if total_shortfall_all > 0:
        shipping_per_unit = (
            cost_config.shipping.base_cost + cost_config.shipping.per_unit_cost * total_shortfall_all
        ) / total_shortfall_all
    else:
        shipping_per_unit = 0.0
    return unit_price + shipping_per_unit


def _get_crew_weather_multiplier(weather_data: dict, crew_id: str) -> float:
    """Get weather multiplier for a crew from weather data."""
    for crew in weather_data.get("crews", []):
        if crew["crew_id"] == crew_id:
            return crew["time_multiplier"]
    return 1.0


def _apply_cost_optimized_logic(
    shortfall: int,
    nearby_crews: list,
    consumable: str,
    weather_data: dict,
    cost_config: CostConfig,
    total_shortfall_all: int,
) -> tuple[list[BorrowSource], int]:
    """
    Cost-optimized borrow vs order algorithm.

    For each nearby crew, calculates weather-adjusted borrow cost per unit
    and compares to order cost per unit. Borrows from crews where it's
    cheaper, orders the rest.

    Args:
        shortfall: Number of consumables needed
        nearby_crews: List of crews with available spares
        consumable: Name of consumable type
        weather_data: Weather data with multipliers per crew
        cost_config: Cost configuration with pricing
        total_shortfall_all: Total shortfall for shipping amortization

    Returns:
        Tuple of (list[BorrowSource], to_order: int)
    """
    order_cost_per_unit = _calculate_order_cost_per_unit(
        consumable, total_shortfall_all, cost_config
    )

    remaining = shortfall

    # Calculate borrow cost per unit for each crew with available spares
    crew_options = []
    for crew in nearby_crews:
        available = crew["available"][consumable]
        if available <= 0:
            continue

        weather_mult = _get_crew_weather_multiplier(weather_data, crew["crew_id"])
        borrow_cost = _calculate_borrow_cost_per_unit(
            distance=crew["distance"],
            quantity=min(available, remaining),
            weather_multiplier=weather_mult,
            cost_config=cost_config,
        )

        crew_options.append({
            "crew_id": crew["crew_id"],
            "distance": crew["distance"],
            "available": available,
            "borrow_cost_per_unit": borrow_cost,
        })

    # Sort by borrow cost per unit (cheapest first)
    crew_options.sort(key=lambda x: x["borrow_cost_per_unit"])

    # Fill shortage: borrow from crews where cheaper than ordering
    borrows = []

    for option in crew_options:
        if remaining <= 0:
            break

        if option["borrow_cost_per_unit"] < order_cost_per_unit:
            borrow_qty = min(option["available"], remaining)
            borrows.append(BorrowSource(
                crew_id=option["crew_id"],
                quantity=borrow_qty,
                distance=option["distance"],
            ))
            remaining -= borrow_qty

    return borrows, remaining


def compute_cost_summary(
    order_plan: OrderPlan,
    nearby_crews: list,
    weather_data: dict,
    cost_config: CostConfig,
) -> dict:
    """
    Compute cost metadata for each decision in the order plan.

    Returns per-item cost rationale (borrow vs order cost per unit),
    weather info for involved crews, and total estimated cost.

    Args:
        order_plan: The generated order plan
        nearby_crews: List of nearby crews with available spares
        weather_data: Weather data with multipliers per crew
        cost_config: Cost configuration with pricing

    Returns:
        Dict with items cost breakdown, weather, and totals
    """
    # Calculate total shortfall for shipping amortization
    total_shortfall_all = sum(
        max(0, item.total_needed - item.on_hand) for item in order_plan.items
    )

    items_cost = {}
    weather_info = {}
    total_estimated_cost = 0.0
    total_if_all_ordered = 0.0

    for item in order_plan.items:
        shortfall = max(0, item.total_needed - item.on_hand)
        if shortfall <= 0:
            items_cost[item.consumable_name] = {
                "action": "none_needed",
                "shortfall": 0,
            }
            continue

        order_cost_per_unit = _calculate_order_cost_per_unit(
            item.consumable_name, total_shortfall_all, cost_config
        )
        total_if_all_ordered += order_cost_per_unit * shortfall

        # Find best borrow cost per unit among nearby crews
        best_borrow_cost = None
        for crew in nearby_crews:
            available = crew["available"][item.consumable_name]
            if available <= 0:
                continue
            weather_mult = _get_crew_weather_multiplier(weather_data, crew["crew_id"])
            borrow_cost = _calculate_borrow_cost_per_unit(
                distance=crew["distance"],
                quantity=min(available, shortfall),
                weather_multiplier=weather_mult,
                cost_config=cost_config,
            )
            if best_borrow_cost is None or borrow_cost < best_borrow_cost:
                best_borrow_cost = borrow_cost

        # Determine action and costs
        if item.borrow_sources:
            # Calculate actual borrow cost for the quantities borrowed
            borrow_total = 0.0
            for source in item.borrow_sources:
                weather_mult = _get_crew_weather_multiplier(weather_data, source.crew_id)
                trip_cost = (
                    source.distance * 2 * cost_config.travel.cost_per_mile
                    + (source.distance * 2 / cost_config.travel.average_speed_mph)
                    * weather_mult * cost_config.travel.cost_per_hour_labor
                )
                borrow_total += trip_cost

                # Collect weather info for involved crews
                if source.crew_id not in weather_info:
                    for crew_weather in weather_data.get("crews", []):
                        if crew_weather["crew_id"] == source.crew_id:
                            weather_info[source.crew_id] = {
                                "multiplier": crew_weather["time_multiplier"],
                                "condition": crew_weather["condition"],
                            }
                            break

            total_borrowed = sum(s.quantity for s in item.borrow_sources)
            order_portion_cost = item.to_order * order_cost_per_unit if item.to_order > 0 else 0.0
            total_estimated_cost += borrow_total + order_portion_cost

            action = "mixed" if item.to_order > 0 else "borrow"
            items_cost[item.consumable_name] = {
                "action": action,
                "shortfall": shortfall,
                "borrow_cost_per_unit": round(best_borrow_cost, 2) if best_borrow_cost else None,
                "order_cost_per_unit": round(order_cost_per_unit, 2),
                "borrow_total": round(borrow_total, 2),
                "order_total": round(order_portion_cost, 2),
                "savings_per_unit": round(order_cost_per_unit - (best_borrow_cost or 0), 2) if best_borrow_cost else 0,
            }
        elif item.to_order > 0:
            order_total = item.to_order * order_cost_per_unit
            total_estimated_cost += order_total
            items_cost[item.consumable_name] = {
                "action": "order",
                "shortfall": shortfall,
                "borrow_cost_per_unit": round(best_borrow_cost, 2) if best_borrow_cost else None,
                "order_cost_per_unit": round(order_cost_per_unit, 2),
                "borrow_total": None,
                "order_total": round(order_total, 2),
                "savings_per_unit": 0,
            }

    total_savings = total_if_all_ordered - total_estimated_cost

    return {
        "items": items_cost,
        "weather": weather_info,
        "total_estimated_cost": round(total_estimated_cost, 2),
        "total_if_all_ordered": round(total_if_all_ordered, 2),
        "total_savings": round(total_savings, 2),
    }


def _apply_proximity_logic(
    shortfall: int,
    nearby_crews: list,
    consumable: str,
) -> tuple[list[BorrowSource], int]:
    """
    Proximity-first borrow algorithm (legacy fallback).

    1. Check if any single crew can fully fulfill → use closest one
    2. If not, accumulate from closest to furthest
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
