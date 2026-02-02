"""
LangChain agent orchestration for the frac consumables planner.

Refactored to use LangGraph StateGraph patterns:
1. Decomposition: Distinct nodes instead of a single ReAct mega-agent.
2. Pure Functions: Nodes only update state, no global variables (`_context`).
3. State Management: TypedDict for reliable state passing.
"""

from typing import TypedDict, Optional, Dict, Any
from langgraph.graph import StateGraph, END

from schemas.crew import CrewData
from schemas.order import OrderPlan
from tools.needs_calculator import calculate_needs
from tools.inventory_reader import read_inventory
from tools.order_planner import plan_order, compute_cost_summary
from tools.weather_checker import check_weather
from tools.cost_calculator import load_cost_config


class PlannerState(TypedDict):
    """The typed state representing the workflow execution context."""
    crew_data: CrewData
    weather_seed: Optional[int]
    crew_a_id: str
    job_duration_hours: int
    needs: Optional[Dict]
    inventory: Optional[Dict]
    weather_data: Optional[Dict]
    cost_config: Optional[Dict]
    order_plan: Optional[Any]
    recommendation: Optional[str]
    cost_summary: Optional[Dict]


def extract_crew_info(state: PlannerState) -> dict:
    """Node: Extract job duration and crew ID."""
    crew_data = state["crew_data"]
    crew_a = next((c for c in crew_data.crews if c.distance_to_crew_a is None), None)
    if not crew_a:
        raise ValueError("Crew A not found")
    return {"crew_a_id": "A", "job_duration_hours": crew_a.job_duration_hours}


def calc_needs_node(state: PlannerState) -> dict:
    """Node: Calculate consumable needs."""
    needs = calculate_needs(state["crew_data"], state["crew_a_id"])
    return {"needs": needs}


def read_inventory_node(state: PlannerState) -> dict:
    """Node: Identify spares and nearby crew inventory."""
    inventory_result = read_inventory(state["crew_data"])
    return {"inventory": inventory_result}


def gather_context_node(state: PlannerState) -> dict:
    """Node: Gather weather and cost configuration."""
    weather_data = check_weather.invoke({"crew_data": state["crew_data"], "seed": state.get("weather_seed", 42)})
    cost_config = load_cost_config()
    return {"weather_data": weather_data, "cost_config": cost_config}


def plan_order_node(state: PlannerState) -> dict:
    """Node: Plan the order utilizing borrow-first strategy."""
    order_plan = plan_order(
        needs=state["needs"],
        crew_a_spares=state["inventory"]["crew_a_spares"],
        nearby_crews=state["inventory"]["nearby_crews"],
        crew_id=state["crew_a_id"],
        job_duration_hours=state["job_duration_hours"],
        weather_data=state["weather_data"],
        cost_config=state["cost_config"],
    )
    return {"order_plan": order_plan}


def _generate_recommendation(order_plan: OrderPlan, nearby_crews: list) -> str:
    """Generate a human-readable recommendation from the order plan."""
    lines = [f"**Order Plan for Crew {order_plan.crew_id}** ({order_plan.job_duration_hours}-hour job)\n"]
    for item in order_plan.items:
        display_name = item.consumable_name.replace("_", " ").title()
        if item.total_needed == 0:
            lines.append(f"- **{display_name}**: No replacement needed")
            continue
            
        shortfall = max(0, item.total_needed - item.on_hand)
        lines.append(f"- **{display_name}**: Need {item.total_needed}, have {item.on_hand} on hand")
        
        if shortfall > 0:
            if item.borrow_sources:
                borrow_details = ", ".join([
                    f"Crew {b.crew_id} ({b.quantity} units, {b.distance} mi)"
                    for b in item.borrow_sources
                ])
                total_borrowed = sum(b.quantity for b in item.borrow_sources)
                lines.append(f"  - Borrow {total_borrowed}: {borrow_details}")
            if item.to_order > 0:
                lines.append(f"  - **Order {item.to_order}** from supplier")
            else:
                lines.append(f"  - ✓ Fully covered by borrowing")
        else:
            lines.append(f"  - ✓ Covered by on-hand spares")

    total_to_order = sum(item.to_order for item in order_plan.items)
    total_to_borrow = sum(sum(b.quantity for b in item.borrow_sources) for item in order_plan.items)
    lines.append(f"\n**Summary**: Borrow {total_to_borrow} total, order {total_to_order} total from supplier.")

    return "\n".join(lines)


def generate_recommendation_node(state: PlannerState) -> dict:
    """Node: Generate human-readable recommendation and cost summary."""
    order_plan = state["order_plan"]
    nearby_crews = state["inventory"]["nearby_crews"]

    recommendation = _generate_recommendation(order_plan, nearby_crews)
    cost_summary = compute_cost_summary(order_plan, nearby_crews, state["weather_data"], state["cost_config"])

    return {"recommendation": recommendation, "cost_summary": cost_summary}


def create_agent(model: str = "llama3"):
    """
    Creates the workflow StateGraph.
    Args:
        model: Model parameter (kept for backward compatibility, though execution is now deterministic).
    Returns:
        Compiled LangGraph instance.
    """
    workflow = StateGraph(PlannerState)
    
    # Add nodes
    workflow.add_node("extract_crew_info", extract_crew_info)
    workflow.add_node("calc_needs", calc_needs_node)
    workflow.add_node("read_inventory", read_inventory_node)
    workflow.add_node("gather_context", gather_context_node)
    workflow.add_node("plan_order", plan_order_node)
    workflow.add_node("generate_recommendation", generate_recommendation_node)

    # Define edges
    workflow.set_entry_point("extract_crew_info")
    workflow.add_edge("extract_crew_info", "calc_needs")
    workflow.add_edge("calc_needs", "read_inventory")
    workflow.add_edge("read_inventory", "gather_context")
    workflow.add_edge("gather_context", "plan_order")
    workflow.add_edge("plan_order", "generate_recommendation")
    workflow.add_edge("generate_recommendation", END)

    return workflow.compile()


def run_agent(agent, crew_data: CrewData, weather_seed: int | None = 42) -> dict:
    """
    Execute the workflow agent.
    
    Args:
        agent: Compiled LangGraph agent
        crew_data: Crew data payload
        weather_seed: Random seed for weather simulator
        
    Returns:
        Dict matching the original UI expected schema.
    """
    initial_state = {
        "crew_data": crew_data,
        "weather_seed": weather_seed,
        "crew_a_id": "",
        "job_duration_hours": 0,
        "needs": None,
        "inventory": None,
        "weather_data": None,
        "cost_config": None,
        "order_plan": None,
        "recommendation": None,
        "cost_summary": None
    }
    
    # Execute graph
    result = agent.invoke(initial_state)
    
    return {
        "recommendation": result["recommendation"],
        "order_plan": result["order_plan"],
        "weather_data": result["weather_data"],
        "cost_summary": result["cost_summary"],
    }
