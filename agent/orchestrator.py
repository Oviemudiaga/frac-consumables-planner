"""
LangChain agent orchestration for the frac consumables planner.

This module creates and configures the LangChain agent that:
- Binds the three tools (needs_calculator, inventory_reader, order_planner)
- Uses the system prompt from prompts.py
- Orchestrates the tool calls to generate an order plan

The agent flow:
1. Receive CrewData from the UI
2. Call calculate_needs to determine what Crew A needs
3. Call read_inventory to get spares and nearby crew availability
4. Call plan_order to generate the borrow/order plan
5. Return recommendation and OrderPlan to the UI

Usage:
    from agent.orchestrator import create_agent, run_agent

    agent = create_agent()
    result = run_agent(agent, crew_data)
"""

import json

from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from schemas.crew import CrewData, Spares
from schemas.order import OrderPlan
from tools.needs_calculator import calculate_needs
from tools.inventory_reader import read_inventory
from tools.order_planner import plan_order
from prompts.prompts import SYSTEM_PROMPT


# Module-level context to share CrewData with tools
_context: dict = {}


@tool
def calculate_needs_tool(crew_id: str = "A") -> str:
    """Calculate consumable replacement needs for a crew.

    Analyzes the crew's pumps and determines which consumables need
    replacement based on remaining life vs job duration.

    Args:
        crew_id: ID of the crew to analyze (default "A")

    Returns:
        JSON string with needs per consumable type showing pumps_needing and total_needed.
    """
    crew_data = _context["crew_data"]
    result = calculate_needs(crew_data, crew_id)
    return json.dumps(result, indent=2)


@tool
def read_inventory_tool() -> str:
    """Read crew inventory and nearby crew availability.

    Gets Crew A's spare parts on hand and identifies nearby crews
    (within proximity threshold) that have available inventory to lend.

    Returns:
        JSON string with crew_a_spares and nearby_crews list sorted by distance.
    """
    crew_data = _context["crew_data"]
    result = read_inventory(crew_data)

    # Convert Spares object to dict for JSON serialization
    serialized = {
        "crew_a_spares": {
            "valve_packings": result["crew_a_spares"].valve_packings,
            "seals": result["crew_a_spares"].seals,
            "plungers": result["crew_a_spares"].plungers
        },
        "nearby_crews": result["nearby_crews"]
    }
    return json.dumps(serialized, indent=2)


@tool
def plan_order_tool(needs_json: str, inventory_json: str) -> str:
    """Plan the order using borrow-first strategy.

    Takes the needs and inventory data and generates an optimized order plan
    that prioritizes borrowing from nearby crews before ordering from suppliers.

    Args:
        needs_json: JSON string from calculate_needs_tool
        inventory_json: JSON string from read_inventory_tool

    Returns:
        JSON string with the complete order plan including borrow sources
        and quantities to order from suppliers.
    """
    crew_data = _context["crew_data"]

    # Parse inputs
    needs = json.loads(needs_json)
    inventory = json.loads(inventory_json)

    # Find Crew A to get job duration
    crew_a = None
    for crew in crew_data.crews:
        if crew.distance_to_crew_a is None:
            crew_a = crew
            break

    if crew_a is None:
        raise ValueError("Crew A not found")

    # Reconstruct Spares object
    crew_a_spares = Spares(**inventory["crew_a_spares"])

    # Call the order planner
    order_plan = plan_order(
        needs=needs,
        crew_a_spares=crew_a_spares,
        nearby_crews=inventory["nearby_crews"],
        crew_id="A",
        job_duration_hours=crew_a.job_duration_hours
    )

    # Store in context for extraction
    _context["order_plan"] = order_plan

    return order_plan.model_dump_json(indent=2)


def create_agent(model: str = "llama3"):
    """
    Create a LangChain agent with consumables planner tools.

    Args:
        model: Ollama model name to use (default "llama3")

    Returns:
        Configured LangGraph agent with tools bound
    """
    # Initialize the LLM
    llm = ChatOllama(model=model, temperature=0)

    # Collect tools
    tools = [calculate_needs_tool, read_inventory_tool, plan_order_tool]

    # Create the ReAct agent using LangGraph
    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT
    )

    return agent


def run_agent(agent, crew_data: CrewData) -> dict:
    """
    Run the agent to generate an order plan.

    Args:
        agent: LangGraph compiled agent
        crew_data: CrewData to analyze

    Returns:
        Dict with recommendation (str) and order_plan (OrderPlan)
    """
    # Store crew_data in context for tools to access
    _context["crew_data"] = crew_data
    _context["order_plan"] = None

    # Find Crew A to get job info for the prompt
    crew_a = None
    for crew in crew_data.crews:
        if crew.distance_to_crew_a is None:
            crew_a = crew
            break

    if crew_a is None:
        raise ValueError("Crew A not found")

    # Create the input prompt
    input_message = (
        f"Analyze Crew A's consumable needs for their upcoming {crew_a.job_duration_hours}-hour job. "
        f"They have {len(crew_a.pumps)} pumps. "
        f"The proximity threshold for nearby crews is {crew_data.proximity_threshold_miles} miles. "
        f"Each pump requires {crew_data.consumables_per_pump} of each consumable type. "
        "Generate an order plan and provide a recommendation."
    )

    # Run the agent - LangGraph agents use invoke with messages
    result = agent.invoke({"messages": [("user", input_message)]})

    # Extract the final response from messages
    messages = result.get("messages", [])
    recommendation = "No recommendation generated."

    # Get the last AI message as the recommendation
    for msg in reversed(messages):
        if hasattr(msg, 'content') and msg.type == "ai" and msg.content:
            # Skip tool call messages
            if not hasattr(msg, 'tool_calls') or not msg.tool_calls:
                recommendation = msg.content
                break

    # Get order_plan from context (stored by plan_order_tool)
    order_plan = _context.get("order_plan")

    if order_plan is None:
        raise RuntimeError("Agent did not generate an order plan. The plan_order_tool was not called.")

    return {
        "recommendation": recommendation,
        "order_plan": order_plan
    }
