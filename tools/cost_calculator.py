"""
Cost calculation tool for the Cost Analyzer Agent.

This tool calculates and compares costs for borrowing vs ordering
consumables, providing cost breakdowns and recommendations.

Usage:
    from tools.cost_calculator import calculate_borrow_cost, calculate_order_cost, compare_costs

    borrow_cost = calculate_borrow_cost(transfer_plan, cost_config)
    order_cost = calculate_order_cost(order_plan, cost_config)
    comparison = compare_costs(order_plan, transfer_plan, cost_config)
"""

import json
from langchain_core.tools import tool

from schemas.order import OrderPlan
from schemas.transfer import TransferPlan
from schemas.cost import CostConfig, CostBreakdown, ItemCostBreakdown


def load_cost_config(config_path: str = "data/examples/cost_config.json") -> CostConfig:
    """Load cost configuration from JSON file."""
    try:
        with open(config_path) as f:
            data = json.load(f)
            return CostConfig(**data)
    except FileNotFoundError:
        # Return defaults if file not found
        return CostConfig()


@tool
def calculate_borrow_cost(
    transfer_plan: dict,
    cost_config: dict | None = None
) -> dict:
    """
    Calculate the total cost of borrowing items via transfer.

    Cost includes:
    - Travel cost: distance × $/mile
    - Labor cost: adjusted travel time × $/hour

    Args:
        transfer_plan: TransferPlan dict with route and timing
        cost_config: Optional CostConfig dict (uses defaults if not provided)

    Returns:
        Dict with travel_cost, labor_cost, and total_cost
    """
    # Parse inputs
    if isinstance(transfer_plan, dict):
        plan = TransferPlan(**transfer_plan)
    else:
        plan = transfer_plan

    if cost_config is None:
        config = load_cost_config()
    elif isinstance(cost_config, dict):
        config = CostConfig(**cost_config)
    else:
        config = cost_config

    # Calculate costs
    travel_cost = plan.total_distance_miles * config.travel.cost_per_mile
    labor_cost = plan.total_adjusted_time_hours * config.travel.cost_per_hour_labor
    total_cost = travel_cost + labor_cost

    return {
        "distance_miles": plan.total_distance_miles,
        "travel_time_hours": plan.total_adjusted_time_hours,
        "travel_cost": round(travel_cost, 2),
        "labor_cost": round(labor_cost, 2),
        "total_cost": round(total_cost, 2),
        "breakdown": {
            "travel": f"${travel_cost:.2f} ({plan.total_distance_miles} mi × ${config.travel.cost_per_mile}/mi)",
            "labor": f"${labor_cost:.2f} ({plan.total_adjusted_time_hours:.2f} hr × ${config.travel.cost_per_hour_labor}/hr)",
        }
    }


@tool
def calculate_order_cost(
    order_plan: dict,
    cost_config: dict | None = None
) -> dict:
    """
    Calculate the total cost of ordering items from suppliers.

    Cost includes:
    - Parts cost: quantity × unit price per consumable
    - Shipping cost: base cost + (total units × per unit cost)

    Args:
        order_plan: OrderPlan dict with items to order
        cost_config: Optional CostConfig dict (uses defaults if not provided)

    Returns:
        Dict with parts_cost, shipping_cost, total_cost, and per-item breakdown
    """
    # Parse inputs
    if isinstance(order_plan, dict):
        plan = OrderPlan(**order_plan)
    else:
        plan = order_plan

    if cost_config is None:
        config = load_cost_config()
    elif isinstance(cost_config, dict):
        config = CostConfig(**cost_config)
    else:
        config = cost_config

    # Calculate parts cost
    parts_breakdown = {}
    total_parts_cost = 0.0
    total_units = 0

    for item in plan.items:
        # Calculate what would need to be ordered if not borrowing
        qty_to_order = item.total_needed - item.on_hand
        if qty_to_order <= 0:
            continue

        consumable = item.consumable_name
        if consumable in config.consumables:
            unit_price = config.consumables[consumable].unit_price
            item_cost = qty_to_order * unit_price
            parts_breakdown[consumable] = {
                "quantity": qty_to_order,
                "unit_price": unit_price,
                "cost": round(item_cost, 2),
            }
            total_parts_cost += item_cost
            total_units += qty_to_order

    # Calculate shipping
    if total_units > 0:
        shipping_cost = config.shipping.base_cost + (total_units * config.shipping.per_unit_cost)
    else:
        shipping_cost = 0.0

    total_cost = total_parts_cost + shipping_cost

    return {
        "parts_cost": round(total_parts_cost, 2),
        "shipping_cost": round(shipping_cost, 2),
        "total_cost": round(total_cost, 2),
        "total_units": total_units,
        "parts_breakdown": parts_breakdown,
        "breakdown": {
            "parts": f"${total_parts_cost:.2f} ({total_units} units)",
            "shipping": f"${shipping_cost:.2f} (base ${config.shipping.base_cost} + {total_units} × ${config.shipping.per_unit_cost})",
        }
    }


@tool
def compare_costs(
    order_plan: dict,
    transfer_plan: dict,
    cost_config: dict | None = None
) -> dict:
    """
    Compare borrow vs order costs and provide recommendation.

    Calculates costs for both options and recommends the cheaper one.
    Provides detailed breakdown and savings analysis.

    Args:
        order_plan: OrderPlan dict with items needed
        transfer_plan: TransferPlan dict with route and timing
        cost_config: Optional CostConfig dict

    Returns:
        CostBreakdown dict with comparison and recommendation
    """
    # Parse inputs
    if isinstance(order_plan, dict):
        plan = OrderPlan(**order_plan)
    else:
        plan = order_plan

    if isinstance(transfer_plan, dict):
        t_plan = TransferPlan(**transfer_plan)
    else:
        t_plan = transfer_plan

    if cost_config is None:
        config = load_cost_config()
    elif isinstance(cost_config, dict):
        config = CostConfig(**cost_config)
    else:
        config = cost_config

    # Calculate borrow cost (travel + labor)
    borrow_result = calculate_borrow_cost.invoke({
        "transfer_plan": t_plan.model_dump(),
        "cost_config": config.model_dump(),
    })

    # Calculate order cost (parts + shipping) for items we're borrowing
    # This shows what it would cost if we ordered instead of borrowing
    order_result = calculate_order_cost.invoke({
        "order_plan": plan.model_dump(),
        "cost_config": config.model_dump(),
    })

    total_borrow = borrow_result["total_cost"]
    total_order = order_result["total_cost"]

    # Determine recommendation
    if total_borrow < total_order:
        recommendation = "borrow"
        savings = total_order - total_borrow
        savings_pct = (savings / total_order * 100) if total_order > 0 else 0
        summary = f"BORROW recommended - saves ${savings:.2f} ({savings_pct:.1f}%)"
    elif total_order < total_borrow:
        recommendation = "order"
        savings = total_borrow - total_order
        savings_pct = (savings / total_borrow * 100) if total_borrow > 0 else 0
        summary = f"ORDER recommended - saves ${savings:.2f} ({savings_pct:.1f}%)"
    else:
        recommendation = "either"
        savings = 0.0
        summary = "Costs are equal - either option works"

    # Build per-item breakdown
    items = []
    for item in plan.items:
        consumable = item.consumable_name
        qty_needed = item.total_needed - item.on_hand
        if qty_needed <= 0:
            items.append(ItemCostBreakdown(
                consumable=consumable,
                quantity=0,
                borrow_cost=0.0,
                order_cost=0.0,
                recommended_action="none_needed",
            ))
            continue

        # Borrow cost is proportional share of travel cost
        borrow_share = borrow_result["total_cost"]  # Simplified: full travel cost for any borrow

        # Order cost from breakdown
        order_share = 0.0
        if consumable in order_result["parts_breakdown"]:
            order_share = order_result["parts_breakdown"][consumable]["cost"]

        # Per-item recommendation
        if item.borrow_sources:
            action = "borrow"
        elif item.to_order > 0:
            action = "order"
        else:
            action = "none_needed"

        items.append(ItemCostBreakdown(
            consumable=consumable,
            quantity=qty_needed,
            borrow_cost=round(borrow_share, 2),
            order_cost=round(order_share, 2),
            recommended_action=action,
        ))

    cost_breakdown = CostBreakdown(
        items=items,
        travel_cost=borrow_result["travel_cost"] + borrow_result["labor_cost"],
        total_borrow_cost=total_borrow,
        total_order_cost=total_order,
        total_cost=min(total_borrow, total_order),
        savings=savings,
        recommendation=recommendation,
        recommendation_summary=summary,
    )

    return {
        "borrow_option": borrow_result,
        "order_option": order_result,
        "comparison": {
            "borrow_cost": total_borrow,
            "order_cost": total_order,
            "savings": round(savings, 2),
            "recommendation": recommendation,
            "summary": summary,
        },
        "breakdown": cost_breakdown.model_dump(),
    }


def format_cost_comparison(comparison: dict) -> str:
    """
    Format cost comparison as human-readable text.

    Args:
        comparison: Result from compare_costs

    Returns:
        Formatted string summary
    """
    borrow = comparison["borrow_option"]
    order = comparison["order_option"]
    comp = comparison["comparison"]

    lines = [
        "Cost Analysis",
        "=" * 40,
        "",
        "BORROW Option:",
        f"  Travel: {borrow['breakdown']['travel']}",
        f"  Labor: {borrow['breakdown']['labor']}",
        f"  Total: ${borrow['total_cost']:.2f}",
        "",
        "ORDER Option:",
        f"  Parts: {order['breakdown']['parts']}",
        f"  Shipping: {order['breakdown']['shipping']}",
        f"  Total: ${order['total_cost']:.2f}",
        "",
        "-" * 40,
        f"RECOMMENDATION: {comp['summary']}",
    ]

    return "\n".join(lines)
