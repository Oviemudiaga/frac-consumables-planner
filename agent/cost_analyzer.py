"""
Cost Analyzer Agent for comparing borrow vs order costs.

Refactored to use LangGraph StateGraph patterns:
1. Decomposition: Distinct nodes instead of a single ReAct mega-agent.
2. Pure Functions: Nodes only update state, no global variables (`_cost_context`).
3. State Management: TypedDict for reliable state passing.
"""

from typing import TypedDict, Optional, Any
from langgraph.graph import StateGraph, END

from schemas.order import OrderPlan
from schemas.transfer import TransferPlan
from schemas.cost import CostConfig
from tools.cost_calculator import (
    calculate_borrow_cost,
    calculate_order_cost,
    compare_costs,
    format_cost_comparison,
    load_cost_config,
)


class CostState(TypedDict):
    """The typed state for the cost analyzer workflow."""
    order_plan: OrderPlan
    transfer_plan: TransferPlan
    cost_config: Optional[Any]
    borrow_cost: Optional[dict]
    order_cost: Optional[dict]
    comparison: Optional[dict]
    summary: Optional[str]


def load_config_node(state: CostState) -> dict:
    """Node: Load cost configuration if not provided."""
    cost_config = state.get("cost_config")
    if cost_config is None:
        cost_config = load_cost_config()
    return {"cost_config": cost_config}


def calc_borrow_cost_node(state: CostState) -> dict:
    """Node: Calculate the cost of borrowing via transfer."""
    borrow_result = calculate_borrow_cost.invoke({
        "transfer_plan": state["transfer_plan"].model_dump(),
        "cost_config": state["cost_config"].model_dump(),
    })
    return {"borrow_cost": borrow_result}


def calc_order_cost_node(state: CostState) -> dict:
    """Node: Calculate the cost of ordering from suppliers."""
    order_result = calculate_order_cost.invoke({
        "order_plan": state["order_plan"].model_dump(),
        "cost_config": state["cost_config"].model_dump(),
    })
    return {"order_cost": order_result}


def compare_costs_node(state: CostState) -> dict:
    """Node: Compare borrow vs order costs and generate recommendation."""
    comparison = compare_costs.invoke({
        "order_plan": state["order_plan"].model_dump(),
        "transfer_plan": state["transfer_plan"].model_dump(),
        "cost_config": state["cost_config"].model_dump(),
    })
    summary = format_cost_comparison(comparison)
    return {"comparison": comparison, "summary": summary}


def create_cost_agent(model: str = "llama3"):
    """
    Creates the cost analyzer StateGraph.
    Args:
        model: Model parameter (kept for backward compatibility).
    Returns:
        Compiled LangGraph instance.
    """
    workflow = StateGraph(CostState)

    workflow.add_node("load_config", load_config_node)
    workflow.add_node("calc_borrow_cost", calc_borrow_cost_node)
    workflow.add_node("calc_order_cost", calc_order_cost_node)
    workflow.add_node("compare_costs", compare_costs_node)

    workflow.set_entry_point("load_config")
    workflow.add_edge("load_config", "calc_borrow_cost")
    workflow.add_edge("calc_borrow_cost", "calc_order_cost")
    workflow.add_edge("calc_order_cost", "compare_costs")
    workflow.add_edge("compare_costs", END)

    return workflow.compile()


def _run_deterministic_cost_analysis(
    order_plan: OrderPlan,
    transfer_plan: TransferPlan,
    cost_config: CostConfig | None = None,
) -> dict:
    """
    Run cost analysis in a deterministic sequence.

    Args:
        order_plan: OrderPlan with items needed
        transfer_plan: TransferPlan with route and timing
        cost_config: Optional CostConfig (uses defaults if not provided)

    Returns:
        Dict with borrow_cost, order_cost, comparison, and summary
    """
    agent = create_cost_agent()
    initial_state = {
        "order_plan": order_plan,
        "transfer_plan": transfer_plan,
        "cost_config": cost_config,
        "borrow_cost": None,
        "order_cost": None,
        "comparison": None,
        "summary": None,
    }
    result = agent.invoke(initial_state)

    return {
        "borrow_cost": result["borrow_cost"],
        "order_cost": result["order_cost"],
        "comparison": result["comparison"],
        "cost_config": result["cost_config"],
        "summary": result["summary"],
    }


def run_cost_agent(
    agent,
    order_plan: OrderPlan,
    transfer_plan: TransferPlan,
    cost_config: CostConfig | None = None,
) -> dict:
    """
    Run the cost analyzer agent to compare costs.

    Args:
        agent: LangGraph compiled agent (can be None for deterministic mode)
        order_plan: OrderPlan from the order planning agent
        transfer_plan: TransferPlan from the transfer coordinator
        cost_config: Optional CostConfig (loads from file if not provided)

    Returns:
        Dict with borrow_cost, order_cost, comparison, and summary
    """
    # Check if there's anything to analyze
    has_needs = any(
        (item.total_needed - item.on_hand) > 0
        for item in order_plan.items
    )

    if not has_needs:
        return {
            "borrow_cost": {"total_cost": 0.0},
            "order_cost": {"total_cost": 0.0},
            "comparison": {
                "borrow_option": {"total_cost": 0.0},
                "order_option": {"total_cost": 0.0},
                "comparison": {
                    "borrow_cost": 0.0,
                    "order_cost": 0.0,
                    "savings": 0.0,
                    "recommendation": "none_needed",
                    "summary": "No items needed - no cost analysis required",
                },
            },
            "summary": "No items needed - all consumables covered by on-hand spares.",
        }

    return _run_deterministic_cost_analysis(order_plan, transfer_plan, cost_config)
