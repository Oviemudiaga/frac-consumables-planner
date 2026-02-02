"""
Agent orchestrator for consumables planning.

This module creates and manages the LangChain agent that:
1. Receives user requests (pumps, hours)
2. Calls tools in sequence (calculate needs, read inventory, plan order)
3. Returns structured OrderPlan + natural language recommendation

Architecture:
  - Uses Ollama with llama3 model
  - Tools bound from tools/ module
  - System prompt from prompts/prompts.py
  - Returns Pydantic OrderPlan for UI rendering

Key Functions:
  - create_agent(): Initialize agent with tools and LLM
  - run_planning_session(): Execute full planning workflow
"""

from langchain_ollama import OllamaLLM
from langchain.agents import AgentExecutor, create_react_agent
from schemas.order import OrderPlan


def create_agent() -> AgentExecutor:
    """
    Create the consumables planning agent.

    Returns:
        AgentExecutor configured with tools and LLM

    Configuration:
        - LLM: Ollama llama3
        - Tools: calculate_consumables_needed, read_crew_inventory, plan_order
        - Prompt: System prompt from prompts.py
    """
    # Implementation will be added in Phase 4
    ...


def run_planning_session(pumps: int, hours: int, crew_id: str = "A") -> OrderPlan:
    """
    Run a complete planning session.

    Args:
        pumps: Number of pumps for the job
        hours: Job duration in hours
        crew_id: Requesting crew's ID

    Returns:
        OrderPlan with recommendations and order details

    Process:
        1. Calculate needs
        2. Read available inventory
        3. Plan borrowing and ordering
        4. Return structured result
    """
    # Implementation will be added in Phase 4
    ...
