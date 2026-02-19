"""
Transfer Coordinator Agent for planning consumable transfers between crews.

This agent coordinates the logistics of transferring consumables:
- Checks weather conditions at all crew locations
- Plans optimal pickup routes
- Calculates weather-adjusted travel times

The agent flow:
1. Receive OrderPlan from the Order Planning Agent
2. Check weather at all relevant crew locations
3. Plan transfer route with weather-adjusted timing
4. Return TransferPlan to the Cost Analyzer Agent

Usage:
    from agent.transfer_coordinator import create_transfer_agent, run_transfer_agent

    agent = create_transfer_agent()
    result = run_transfer_agent(agent, order_plan, crew_data)
"""

import json

from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from schemas.crew import CrewData
from schemas.order import OrderPlan
from schemas.transfer import TransferPlan
from tools.weather_checker import check_weather, get_route_weather, get_weather_for_crews
from tools.route_planner import plan_transfer_route, format_transfer_plan
from prompts.transfer_prompts import TRANSFER_COORDINATOR_PROMPT


# Module-level context to share data with tools
_transfer_context: dict = {}


@tool
def check_weather_tool(seed: int | None = None) -> str:
    """Check weather conditions at all crew locations.

    Gets current weather including temperature, wind, visibility,
    and travel time multipliers for each crew location.

    Args:
        seed: Optional random seed for reproducible weather (for testing)

    Returns:
        JSON string with weather data per crew and a summary.
    """
    crew_data = _transfer_context["crew_data"]
    result = check_weather.invoke({"crew_data": crew_data, "seed": seed})
    _transfer_context["weather_data"] = result
    return json.dumps(result, indent=2)


@tool
def get_route_weather_tool(from_crew: str, to_crew: str) -> str:
    """Get weather conditions for a specific route between two crews.

    Calculates the effective weather multiplier by averaging conditions
    at origin and destination. Warns about hazardous conditions.

    Args:
        from_crew: Origin crew ID
        to_crew: Destination crew ID

    Returns:
        JSON string with route weather including effective multiplier and warnings.
    """
    crew_data = _transfer_context["crew_data"]
    weather_data = _transfer_context.get("weather_data")

    result = get_route_weather.invoke({
        "crew_data": crew_data,
        "from_crew": from_crew,
        "to_crew": to_crew,
        "weather_data": weather_data,
    })
    return json.dumps(result, indent=2)


@tool
def plan_route_tool() -> str:
    """Plan the optimal transfer route for picking up borrowed items.

    Creates a transfer plan with:
    - Route segments sorted by distance (nearest first)
    - Weather-adjusted travel times
    - Pickup manifest showing what to get from each crew

    Returns:
        JSON string with complete TransferPlan.
    """
    crew_data = _transfer_context["crew_data"]
    order_plan = _transfer_context["order_plan"]
    weather_data = _transfer_context.get("weather_data")

    # Ensure we have weather data
    if weather_data is None:
        weather_data = check_weather.invoke({"crew_data": crew_data})
        _transfer_context["weather_data"] = weather_data

    result = plan_transfer_route.invoke({
        "order_plan": order_plan.model_dump(),
        "crew_data": crew_data.model_dump(),
        "weather_data": weather_data,
    })

    # Store for extraction
    _transfer_context["transfer_plan"] = TransferPlan(**result)

    return json.dumps(result, indent=2)


def create_transfer_agent(model: str = "llama3"):
    """
    Create a Transfer Coordinator agent with route planning tools.

    Args:
        model: Ollama model name to use (default "llama3")

    Returns:
        Configured LangGraph agent with tools bound
    """
    llm = ChatOllama(model=model, temperature=0)

    tools = [check_weather_tool, get_route_weather_tool, plan_route_tool]

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=TRANSFER_COORDINATOR_PROMPT
    )

    return agent


def _run_deterministic_transfer(
    order_plan: OrderPlan,
    crew_data: CrewData,
    weather_seed: int | None = None
) -> dict:
    """
    Run the transfer planning in a deterministic sequence.

    This is the primary execution path since we want consistent results.

    Args:
        order_plan: OrderPlan with borrow sources
        crew_data: CrewData with crew information
        weather_seed: Optional seed for reproducible weather

    Returns:
        Dict with transfer_plan (TransferPlan) and weather_data
    """
    # Step 1: Check weather
    weather_data = check_weather.invoke({"crew_data": crew_data, "seed": weather_seed})

    # Step 2: Plan route
    transfer_plan_dict = plan_transfer_route.invoke({
        "order_plan": order_plan.model_dump(),
        "crew_data": crew_data.model_dump(),
        "weather_data": weather_data,
    })

    transfer_plan = TransferPlan(**transfer_plan_dict)

    # Generate summary
    summary = format_transfer_plan(transfer_plan)

    return {
        "transfer_plan": transfer_plan,
        "weather_data": weather_data,
        "summary": summary,
    }


def run_transfer_agent(
    agent,
    order_plan: OrderPlan,
    crew_data: CrewData,
    weather_seed: int | None = None
) -> dict:
    """
    Run the transfer coordinator agent to plan transfers.

    Falls back to deterministic pipeline for consistent results.

    Args:
        agent: LangGraph compiled agent (can be None for deterministic mode)
        order_plan: OrderPlan from the order planning agent
        crew_data: CrewData with crew information
        weather_seed: Optional seed for reproducible weather

    Returns:
        Dict with transfer_plan (TransferPlan), weather_data, and summary
    """
    # Store in context for tools
    _transfer_context["crew_data"] = crew_data
    _transfer_context["order_plan"] = order_plan
    _transfer_context["transfer_plan"] = None
    _transfer_context["weather_data"] = None

    # Check if there's anything to transfer
    has_borrows = any(
        item.borrow_sources for item in order_plan.items
    )

    if not has_borrows:
        # No transfers needed
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

    # Use deterministic pipeline for consistent results
    return _run_deterministic_transfer(order_plan, crew_data, weather_seed)
