"""
LangChain tools for consumables planning.

This module contains custom tools that the LangChain agent uses to:
1. Calculate consumables needed based on job parameters
2. Read inventory from nearby crews
3. Plan borrowing and ordering strategies

Each tool is a function decorated with @tool that returns structured data.
"""
