"""
System prompts and prompt templates for the consumables planner agent.

This module contains all prompts used by the LangChain agent:
- SYSTEM_PROMPT: Main system prompt defining agent behavior
- Any additional prompt templates for tool formatting

The system prompt instructs the agent to:
1. Analyze Crew A's consumable needs
2. Check inventory and nearby crew availability
3. Apply the borrow-first strategy
4. Generate a clear recommendation and order plan

Usage:
    from prompts.prompts import SYSTEM_PROMPT

    agent = create_agent(system_prompt=SYSTEM_PROMPT)
"""

# System prompt for the consumables planner agent
SYSTEM_PROMPT = """
TODO: Implement the system prompt for the consumables planner agent.

The agent should:
1. Analyze Crew A's pump consumable needs
2. Check available spares and nearby crew inventory
3. Apply borrow-first-then-order strategy
4. Generate a clear recommendation with reasoning
"""
