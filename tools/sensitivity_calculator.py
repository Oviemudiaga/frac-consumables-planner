"""
Sensitivity calculator for what-if scenario analysis.

Allows the chatbot to re-run cost calculations with modified parameters
to answer questions like:
- "What if it was storming?"
- "What if Crew B was 30 miles away?"
- "What if parts cost 20% more?"

Usage:
    from tools.sensitivity_calculator import recalculate_sensitivity_tool, set_sensitivity_context

    set_sensitivity_context(order_plan, transfer_plan, cost_config)
    result = recalculate_sensitivity_tool.invoke({...})
"""

import json

from langchain_core.tools import tool

from schemas.cost import CostConfig, ConsumablePricing
from schemas.order import OrderPlan
from schemas.transfer import TransferPlan, RouteSegment
from tools.cost_calculator import calculate_borrow_cost, calculate_order_cost, load_cost_config


# Module-level context shared with the tool (same pattern as cost_analyzer.py)
_sensitivity_context: dict = {}

WEATHER_MULTIPLIERS: dict[str, float] = {
    "clear": 1.0,
    "overcast": 1.1,
    "rain": 1.3,
    "heavy rain": 1.3,
    "storm": 1.5,
    "blizzard": 1.5,
}

AVERAGE_SPEED_MPH = 30.0


def set_sensitivity_context(
    order_plan: OrderPlan,
    transfer_plan: TransferPlan,
    cost_config: CostConfig,
) -> None:
    """Store base data for the sensitivity tool to use."""
    _sensitivity_context["order_plan"] = order_plan
    _sensitivity_context["transfer_plan"] = transfer_plan
    _sensitivity_context["cost_config"] = cost_config


@tool
def recalculate_sensitivity(
    weather_scenario: str = "current",
    distance_multiplier: float = 1.0,
    price_change_pct: float = 0.0,
) -> str:
    """
    Recalculate borrow vs order costs with modified scenario parameters.

    Call this for ANY 'what if' question to show how costs change under different conditions.

    Args:
        weather_scenario: Weather condition to simulate: "clear" (1.0x), "rain" (1.3x),
            "storm" (1.5x), or "current" to keep existing weather unchanged.
        distance_multiplier: Multiply all travel distances by this factor.
            E.g., 2.0 doubles distance, 0.5 halves it. Default 1.0 (no change).
        price_change_pct: Percentage change to consumable unit prices.
            E.g., 20.0 for +20% more expensive, -10.0 for 10% cheaper. Default 0.0.

    Returns:
        JSON string with original costs, modified costs, deltas, and whether
        the borrow vs order decision would change.
    """
    order_plan: OrderPlan | None = _sensitivity_context.get("order_plan")
    transfer_plan: TransferPlan | None = _sensitivity_context.get("transfer_plan")
    cost_config: CostConfig = _sensitivity_context.get("cost_config") or load_cost_config()

    if order_plan is None or transfer_plan is None:
        return json.dumps({"error": "No base order plan available. Generate an order plan first."})

    # --- Original costs ---
    original_borrow = calculate_borrow_cost.invoke({
        "transfer_plan": transfer_plan.model_dump(),
        "cost_config": cost_config.model_dump(),
    })
    original_order = calculate_order_cost.invoke({
        "order_plan": order_plan.model_dump(),
        "cost_config": cost_config.model_dump(),
    })

    # --- Modified scenario ---
    modified_tp = _modify_transfer_plan(transfer_plan, weather_scenario, distance_multiplier)
    modified_cc = _modify_cost_config(cost_config, price_change_pct)

    modified_borrow = calculate_borrow_cost.invoke({
        "transfer_plan": modified_tp.model_dump(),
        "cost_config": modified_cc.model_dump(),
    })
    modified_order = calculate_order_cost.invoke({
        "order_plan": order_plan.model_dump(),
        "cost_config": modified_cc.model_dump(),
    })

    # --- Compare decisions ---
    orig_decision = "BORROW" if original_borrow["total_cost"] < original_order["total_cost"] else "ORDER"
    mod_decision = "BORROW" if modified_borrow["total_cost"] < modified_order["total_cost"] else "ORDER"
    decision_flipped = orig_decision != mod_decision

    return json.dumps({
        "scenario": {
            "weather": weather_scenario,
            "distance_multiplier": distance_multiplier,
            "price_change_pct": price_change_pct,
        },
        "original": {
            "borrow_cost": original_borrow["total_cost"],
            "order_cost": original_order["total_cost"],
            "decision": orig_decision,
            "borrow_breakdown": original_borrow["breakdown"],
            "order_breakdown": original_order["breakdown"],
        },
        "modified": {
            "borrow_cost": modified_borrow["total_cost"],
            "order_cost": modified_order["total_cost"],
            "decision": mod_decision,
            "borrow_breakdown": modified_borrow["breakdown"],
            "order_breakdown": modified_order["breakdown"],
        },
        "impact": {
            "borrow_cost_delta": round(modified_borrow["total_cost"] - original_borrow["total_cost"], 2),
            "order_cost_delta": round(modified_order["total_cost"] - original_order["total_cost"], 2),
            "decision_flipped": decision_flipped,
            "summary": (
                f"Decision would change from {orig_decision} to {mod_decision}!"
                if decision_flipped
                else f"Decision remains {orig_decision} (costs change but recommendation holds)"
            ),
        },
    }, indent=2)


def _modify_transfer_plan(
    transfer_plan: TransferPlan,
    weather_scenario: str,
    distance_multiplier: float,
) -> TransferPlan:
    """Return a new TransferPlan with weather/distance modifications applied."""
    if weather_scenario == "current" and distance_multiplier == 1.0:
        return transfer_plan

    target_mult = WEATHER_MULTIPLIERS.get(weather_scenario.lower()) if weather_scenario != "current" else None

    modified_segments = []
    for seg in transfer_plan.segments:
        new_dist = round(seg.distance_miles * distance_multiplier, 2)
        w_mult = target_mult if target_mult is not None else seg.weather_multiplier
        w_cond = weather_scenario if weather_scenario != "current" else seg.weather_condition

        base_time = new_dist / AVERAGE_SPEED_MPH
        adj_time = base_time * w_mult

        modified_segments.append(RouteSegment(
            from_crew=seg.from_crew,
            to_crew=seg.to_crew,
            distance_miles=new_dist,
            base_travel_time_hours=round(base_time, 4),
            weather_condition=w_cond,
            weather_multiplier=w_mult,
            adjusted_travel_time_hours=round(adj_time, 4),
            items_to_pickup=seg.items_to_pickup,
        ))

    total_dist = sum(s.distance_miles for s in modified_segments)
    total_base = sum(s.base_travel_time_hours for s in modified_segments)
    total_adj = sum(s.adjusted_travel_time_hours for s in modified_segments)

    return TransferPlan(
        crew_id=transfer_plan.crew_id,
        segments=modified_segments,
        total_distance_miles=round(total_dist, 2),
        total_base_time_hours=round(total_base, 4),
        total_adjusted_time_hours=round(total_adj, 4),
        weather_delay_hours=round(total_adj - total_base, 4),
        pickup_manifest=transfer_plan.pickup_manifest,
    )


def _modify_cost_config(cost_config: CostConfig, price_change_pct: float) -> CostConfig:
    """Return a new CostConfig with consumable prices scaled by price_change_pct."""
    if price_change_pct == 0.0:
        return cost_config

    multiplier = 1.0 + (price_change_pct / 100.0)
    new_consumables = {
        name: ConsumablePricing(
            unit_price=round(pricing.unit_price * multiplier, 2),
            supplier_lead_time_days=pricing.supplier_lead_time_days,
        )
        for name, pricing in cost_config.consumables.items()
    }

    return CostConfig(
        travel=cost_config.travel,
        consumables=new_consumables,
        shipping=cost_config.shipping,
    )
