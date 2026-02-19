"""
Cost Analyzer Agent for comparing borrow vs order costs.

This agent analyzes the financial impact of order decisions:
- Calculates borrow costs (travel + labor)
- Calculates order costs (parts + shipping)
- Compares options and recommends the cheaper one

The agent flow:
1. Receive OrderPlan and TransferPlan from previous agents
2. Calculate borrow costs based on transfer route
3. Calculate order costs for the same items
4. Compare and provide recommendation with savings

Usage:
    from agent.cost_analyzer import create_cost_agent, run_cost_agent

    agent = create_cost_agent()
    result = run_cost_agent(agent, order_plan, transfer_plan)
"""

import json

from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from schemas.order import OrderPlan
from schemas.transfer import TransferPlan
from schemas.cost import CostConfig, CostBreakdown
from tools.cost_calculator import (
    calculate_borrow_cost,
    calculate_order_cost,
    compare_costs,
    format_cost_comparison,
    load_cost_config,
)
from prompts.cost_prompts import COST_ANALYZER_PROMPT


# Module-level context to share data with tools
_cost_context: dict = {}


@tool
def calculate_borrow_cost_tool() -> str:
    """Calculate the cost of borrowing items via transfer.

    Uses the transfer plan to calculate:
    - Travel cost: distance × $/mile
    - Labor cost: weather-adjusted time × $/hour

    Returns:
        JSON string with travel_cost, labor_cost, and total_cost.
    """
    transfer_plan = _cost_context["transfer_plan"]
    cost_config = _cost_context.get("cost_config")

    result = calculate_borrow_cost.invoke({
        "transfer_plan": transfer_plan.model_dump(),
        "cost_config": cost_config.model_dump() if cost_config else None,
    })

    _cost_context["borrow_cost"] = result
    return json.dumps(result, indent=2)


@tool
def calculate_order_cost_tool() -> str:
    """Calculate the cost of ordering items from suppliers.

    Uses the order plan to calculate:
    - Parts cost: quantity × unit price
    - Shipping cost: base + per unit

    Returns:
        JSON string with parts_cost, shipping_cost, and total_cost.
    """
    order_plan = _cost_context["order_plan"]
    cost_config = _cost_context.get("cost_config")

    result = calculate_order_cost.invoke({
        "order_plan": order_plan.model_dump(),
        "cost_config": cost_config.model_dump() if cost_config else None,
    })

    _cost_context["order_cost"] = result
    return json.dumps(result, indent=2)


@tool
def compare_costs_tool() -> str:
    """Compare borrow vs order costs and provide recommendation.

    Calculates both options and recommends the cheaper one,
    showing savings amount and percentage.

    Returns:
        JSON string with comparison and recommendation.
    """
    order_plan = _cost_context["order_plan"]
    transfer_plan = _cost_context["transfer_plan"]
    cost_config = _cost_context.get("cost_config")

    result = compare_costs.invoke({
        "order_plan": order_plan.model_dump(),
        "transfer_plan": transfer_plan.model_dump(),
        "cost_config": cost_config.model_dump() if cost_config else None,
    })

    _cost_context["comparison"] = result
    return json.dumps(result, indent=2)


def create_cost_agent(model: str = "llama3"):
    """
    Create a Cost Analyzer agent with cost calculation tools.

    Args:
        model: Ollama model name to use (default "llama3")

    Returns:
        Configured LangGraph agent with tools bound
    """
    llm = ChatOllama(model=model, temperature=0)

    tools = [calculate_borrow_cost_tool, calculate_order_cost_tool, compare_costs_tool]

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=COST_ANALYZER_PROMPT
    )

    return agent


def _run_deterministic_cost_analysis(
    order_plan: OrderPlan,
    transfer_plan: TransferPlan,
    cost_config: CostConfig | None = None
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
    if cost_config is None:
        cost_config = load_cost_config()

    # Calculate borrow cost
    borrow_result = calculate_borrow_cost.invoke({
        "transfer_plan": transfer_plan.model_dump(),
        "cost_config": cost_config.model_dump(),
    })

    # Calculate order cost
    order_result = calculate_order_cost.invoke({
        "order_plan": order_plan.model_dump(),
        "cost_config": cost_config.model_dump(),
    })

    # Compare costs
    comparison = compare_costs.invoke({
        "order_plan": order_plan.model_dump(),
        "transfer_plan": transfer_plan.model_dump(),
        "cost_config": cost_config.model_dump(),
    })

    # Generate formatted summary
    summary = format_cost_comparison(comparison)

    return {
        "borrow_cost": borrow_result,
        "order_cost": order_result,
        "comparison": comparison,
        "cost_config": cost_config,
        "summary": summary,
    }


def run_cost_agent(
    agent,
    order_plan: OrderPlan,
    transfer_plan: TransferPlan,
    cost_config: CostConfig | None = None
) -> dict:
    """
    Run the cost analyzer agent to compare costs.

    Uses deterministic pipeline for consistent results.

    Args:
        agent: LangGraph compiled agent (can be None for deterministic mode)
        order_plan: OrderPlan from the order planning agent
        transfer_plan: TransferPlan from the transfer coordinator
        cost_config: Optional CostConfig (loads from file if not provided)

    Returns:
        Dict with borrow_cost, order_cost, comparison, and summary
    """
    # Store in context for tools
    _cost_context["order_plan"] = order_plan
    _cost_context["transfer_plan"] = transfer_plan
    _cost_context["cost_config"] = cost_config or load_cost_config()
    _cost_context["borrow_cost"] = None
    _cost_context["order_cost"] = None
    _cost_context["comparison"] = None

    # Check if there's anything to analyze
    has_needs = any(
        (item.total_needed - item.on_hand) > 0
        for item in order_plan.items
    )

    if not has_needs:
        # No items needed, no cost analysis required
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

    # Use deterministic pipeline for consistent results
    return _run_deterministic_cost_analysis(order_plan, transfer_plan, cost_config)
