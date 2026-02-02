"""
Transfer Coordinator Agent for planning consumable transfers between crews.

Refactored to use LangGraph StateGraph patterns:
1. Decomposition: Distinct nodes instead of a single ReAct mega-agent.
2. Pure Functions: Nodes only update state, no global variables (`_transfer_context`).
3. State Management: TypedDict for reliable state passing.
"""

from typing import TypedDict, Optional, Any
from langgraph.graph import StateGraph, END

from schemas.crew import CrewData
from schemas.order import OrderPlan
from schemas.transfer import TransferPlan
from tools.weather_checker import check_weather
from tools.route_planner import plan_transfer_route, format_transfer_plan


class TransferState(TypedDict):
    """The typed state for the transfer coordinator workflow."""
    order_plan: OrderPlan
    crew_data: CrewData
    weather_seed: Optional[int]
    weather_data: Optional[dict]
    transfer_plan: Optional[Any]
    summary: Optional[str]


def check_weather_node(state: TransferState) -> dict:
    """Node: Check weather at all crew locations."""
    weather_data = check_weather.invoke({
        "crew_data": state["crew_data"],
        "seed": state.get("weather_seed"),
    })
    return {"weather_data": weather_data}


def plan_route_node(state: TransferState) -> dict:
    """Node: Plan the optimal transfer route."""
    transfer_plan_dict = plan_transfer_route.invoke({
        "order_plan": state["order_plan"].model_dump(),
        "crew_data": state["crew_data"].model_dump(),
        "weather_data": state["weather_data"],
    })
    transfer_plan = TransferPlan(**transfer_plan_dict)
    return {"transfer_plan": transfer_plan}


def format_summary_node(state: TransferState) -> dict:
    """Node: Generate a human-readable transfer summary."""
    summary = format_transfer_plan(state["transfer_plan"])
    return {"summary": summary}


def create_transfer_agent(model: str = "llama3"):
    """
    Creates the transfer coordinator StateGraph.
    Args:
        model: Model parameter (kept for backward compatibility).
    Returns:
        Compiled LangGraph instance.
    """
    workflow = StateGraph(TransferState)

    workflow.add_node("check_weather", check_weather_node)
    workflow.add_node("plan_route", plan_route_node)
    workflow.add_node("format_summary", format_summary_node)

    workflow.set_entry_point("check_weather")
    workflow.add_edge("check_weather", "plan_route")
    workflow.add_edge("plan_route", "format_summary")
    workflow.add_edge("format_summary", END)

    return workflow.compile()


def _run_deterministic_transfer(
    order_plan: OrderPlan,
    crew_data: CrewData,
    weather_seed: int | None = None,
) -> dict:
    """
    Run the transfer planning in a deterministic sequence.

    Args:
        order_plan: OrderPlan with borrow sources
        crew_data: CrewData with crew information
        weather_seed: Optional seed for reproducible weather

    Returns:
        Dict with transfer_plan (TransferPlan), weather_data, and summary
    """
    # Check if there's anything to transfer
    has_borrows = any(item.borrow_sources for item in order_plan.items)

    if not has_borrows:
        empty_plan = TransferPlan(
            crew_id=order_plan.crew_id,
            segments=[],
            total_distance_miles=0.0,
            total_base_time_hours=0.0,
            total_adjusted_time_hours=0.0,
            weather_delay_hours=0.0,
            pickup_manifest={},
        )
        return {
            "transfer_plan": empty_plan,
            "weather_data": {"crews": [], "summary": "No weather check needed - no transfers required."},
            "summary": "No transfers needed - all items covered by on-hand spares or ordering.",
        }

    agent = create_transfer_agent()
    initial_state = {
        "order_plan": order_plan,
        "crew_data": crew_data,
        "weather_seed": weather_seed,
        "weather_data": None,
        "transfer_plan": None,
        "summary": None,
    }
    result = agent.invoke(initial_state)

    return {
        "transfer_plan": result["transfer_plan"],
        "weather_data": result["weather_data"],
        "summary": result["summary"],
    }


def run_transfer_agent(
    agent,
    order_plan: OrderPlan,
    crew_data: CrewData,
    weather_seed: int | None = None,
) -> dict:
    """
    Run the transfer coordinator agent to plan transfers.

    Args:
        agent: Compiled LangGraph agent (can be None for deterministic mode)
        order_plan: OrderPlan from the order planning agent
        crew_data: CrewData with crew information
        weather_seed: Optional seed for reproducible weather

    Returns:
        Dict with transfer_plan (TransferPlan), weather_data, and summary
    """
    return _run_deterministic_transfer(order_plan, crew_data, weather_seed)
