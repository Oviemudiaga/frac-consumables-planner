"""
Route planning tool for the Transfer Coordinator Agent.

This tool plans optimal pickup routes considering distance and weather,
creating a TransferPlan with segments, timing, and pickup manifests.

Usage:
    from tools.route_planner import plan_transfer_route

    transfer_plan = plan_transfer_route(order_plan, crew_data, weather_data)
"""

from langchain_core.tools import tool

from schemas.crew import CrewData
from schemas.order import OrderPlan
from schemas.transfer import RouteSegment, TransferPlan
from schemas.weather import WEATHER_MULTIPLIERS, WeatherCondition


# Default average speed for travel calculations
DEFAULT_AVERAGE_SPEED_MPH = 30.0


def _get_distance_between_crews(crew_data: CrewData, from_id: str, to_id: str) -> float:
    """
    Get distance between two crews.

    Uses distance_to_crew_a field and assumes symmetric distances.
    """
    # Find crews
    from_crew = next((c for c in crew_data.crews if c.crew_id == from_id), None)
    to_crew = next((c for c in crew_data.crews if c.crew_id == to_id), None)

    if from_crew is None or to_crew is None:
        return 0.0

    # If one is Crew A, use the other's distance_to_crew_a
    if from_crew.distance_to_crew_a is None:  # from_crew is A
        return to_crew.distance_to_crew_a or 0.0
    elif to_crew.distance_to_crew_a is None:  # to_crew is A
        return from_crew.distance_to_crew_a or 0.0
    else:
        # Both are non-A crews - estimate using triangle (simplified)
        # In reality, you'd calculate from coordinates
        # For now, use the sum of distances to A as upper bound / 2
        return abs(from_crew.distance_to_crew_a - to_crew.distance_to_crew_a)


def _get_weather_multiplier(weather_data: dict, crew_id: str) -> tuple[str, float]:
    """Get weather condition and multiplier for a crew."""
    for crew in weather_data.get("crews", []):
        if crew["crew_id"] == crew_id:
            return crew["condition"], crew["time_multiplier"]
    return "clear", 1.0


@tool
def plan_transfer_route(
    order_plan: dict,
    crew_data: dict,
    weather_data: dict,
    average_speed_mph: float = DEFAULT_AVERAGE_SPEED_MPH
) -> dict:
    """
    Plan optimal pickup route for borrowing consumables from other crews.

    Creates a transfer plan with:
    - Route segments with weather-adjusted travel times
    - Pickup manifest showing what to get from each crew
    - Total distance and time calculations

    Args:
        order_plan: OrderPlan dict with borrow sources
        crew_data: CrewData dict with crew information
        weather_data: Weather data dict from check_weather tool
        average_speed_mph: Average travel speed (default 30 mph)

    Returns:
        TransferPlan dict with segments, timing, and manifest
    """
    # Parse inputs if they're dicts
    if isinstance(crew_data, dict):
        crew_data_obj = CrewData(**{k: v for k, v in crew_data.items() if not k.startswith('_')})
    else:
        crew_data_obj = crew_data

    if isinstance(order_plan, dict):
        order_plan_obj = OrderPlan(**order_plan)
    else:
        order_plan_obj = order_plan

    # Find destination crew (Crew A - the one needing items)
    dest_crew_id = order_plan_obj.crew_id

    # Collect all borrow sources from order plan
    # {crew_id: {consumable: quantity}}
    pickup_manifest: dict[str, dict[str, int]] = {}

    for item in order_plan_obj.items:
        if item.borrow_sources:
            for source in item.borrow_sources:
                if source.crew_id not in pickup_manifest:
                    pickup_manifest[source.crew_id] = {}
                pickup_manifest[source.crew_id][item.consumable_name] = source.quantity

    # If nothing to borrow, return empty plan
    if not pickup_manifest:
        return TransferPlan(
            crew_id=dest_crew_id,
            segments=[],
            total_distance_miles=0.0,
            total_base_time_hours=0.0,
            total_adjusted_time_hours=0.0,
            weather_delay_hours=0.0,
            pickup_manifest={},
        ).model_dump()

    # Sort crews by distance (nearest first for simple greedy route)
    crews_to_visit = []
    for crew_id in pickup_manifest.keys():
        crew = next((c for c in crew_data_obj.crews if c.crew_id == crew_id), None)
        if crew:
            distance = crew.distance_to_crew_a or 0.0
            crews_to_visit.append((crew_id, distance))

    crews_to_visit.sort(key=lambda x: x[1])  # Sort by distance

    # Build route segments
    segments = []
    current_location = dest_crew_id
    total_distance = 0.0
    total_base_time = 0.0
    total_adjusted_time = 0.0

    for crew_id, _ in crews_to_visit:
        # Outbound: current location → pickup crew
        distance = _get_distance_between_crews(crew_data_obj, current_location, crew_id)
        base_time = distance / average_speed_mph if average_speed_mph > 0 else 0.0

        # Get weather at destination
        condition, multiplier = _get_weather_multiplier(weather_data, crew_id)
        adjusted_time = base_time * multiplier

        segment = RouteSegment(
            from_crew=current_location,
            to_crew=crew_id,
            distance_miles=distance,
            base_travel_time_hours=round(base_time, 4),
            weather_condition=condition,
            weather_multiplier=multiplier,
            adjusted_travel_time_hours=round(adjusted_time, 4),
            items_to_pickup=pickup_manifest.get(crew_id, {}),
        )
        segments.append(segment)

        total_distance += distance
        total_base_time += base_time
        total_adjusted_time += adjusted_time
        current_location = crew_id

    # Return trip: last pickup → destination
    if current_location != dest_crew_id:
        distance = _get_distance_between_crews(crew_data_obj, current_location, dest_crew_id)
        base_time = distance / average_speed_mph if average_speed_mph > 0 else 0.0

        # Get weather at destination for return
        condition, multiplier = _get_weather_multiplier(weather_data, dest_crew_id)
        adjusted_time = base_time * multiplier

        segment = RouteSegment(
            from_crew=current_location,
            to_crew=dest_crew_id,
            distance_miles=distance,
            base_travel_time_hours=round(base_time, 4),
            weather_condition=condition,
            weather_multiplier=multiplier,
            adjusted_travel_time_hours=round(adjusted_time, 4),
            items_to_pickup={},  # Return trip, no pickup
        )
        segments.append(segment)

        total_distance += distance
        total_base_time += base_time
        total_adjusted_time += adjusted_time

    weather_delay = total_adjusted_time - total_base_time

    transfer_plan = TransferPlan(
        crew_id=dest_crew_id,
        segments=segments,
        total_distance_miles=round(total_distance, 2),
        total_base_time_hours=round(total_base_time, 4),
        total_adjusted_time_hours=round(total_adjusted_time, 4),
        weather_delay_hours=round(weather_delay, 4),
        pickup_manifest=pickup_manifest,
    )

    return transfer_plan.model_dump()


def format_transfer_plan(transfer_plan: TransferPlan | dict) -> str:
    """
    Format a transfer plan as human-readable text.

    Args:
        transfer_plan: TransferPlan object or dict

    Returns:
        Formatted string summary
    """
    if isinstance(transfer_plan, dict):
        plan = TransferPlan(**transfer_plan)
    else:
        plan = transfer_plan

    if not plan.segments:
        return "No transfers needed - all items available on-hand or via ordering."

    lines = [
        f"Transfer Plan for Crew {plan.crew_id}",
        "=" * 40,
        "",
        "Route:",
    ]

    for i, seg in enumerate(plan.segments, 1):
        pickup_str = ""
        if seg.items_to_pickup:
            items = [f"{v} {k.replace('_', ' ').title()}" for k, v in seg.items_to_pickup.items()]
            pickup_str = f" → Pickup: {', '.join(items)}"

        weather_note = ""
        if seg.weather_multiplier > 1.0:
            weather_note = f" ({seg.weather_condition}, {seg.weather_multiplier}x)"

        time_mins = round(seg.adjusted_travel_time_hours * 60, 1)
        lines.append(
            f"  {i}. {seg.from_crew} → {seg.to_crew}: "
            f"{seg.distance_miles} mi, {time_mins} min{weather_note}{pickup_str}"
        )

    lines.extend([
        "",
        "Summary:",
        f"  Total Distance: {plan.total_distance_miles} miles",
        f"  Base Time: {round(plan.total_base_time_hours * 60, 1)} minutes",
        f"  Weather Delay: +{round(plan.weather_delay_hours * 60, 1)} minutes",
        f"  Adjusted Time: {round(plan.total_adjusted_time_hours * 60, 1)} minutes",
        "",
        "Pickup Manifest:",
    ])

    for crew_id, items in plan.pickup_manifest.items():
        item_strs = [f"{qty} {name.replace('_', ' ').title()}" for name, qty in items.items()]
        lines.append(f"  Crew {crew_id}: {', '.join(item_strs)}")

    return "\n".join(lines)
