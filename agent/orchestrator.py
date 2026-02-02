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


def create_agent():
    """
    Create a LangChain agent with consumables planner tools.

    Returns:
        Configured LangChain agent with tools bound
    """
    # TODO: Implement agent creation with langchain-ollama
    pass


def run_agent(agent, crew_data):
    """
    Run the agent to generate an order plan.

    Args:
        agent: LangChain agent instance
        crew_data: CrewData to analyze

    Returns:
        Dict with recommendation (str) and order_plan (OrderPlan)
    """
    # TODO: Implement agent execution
    pass
