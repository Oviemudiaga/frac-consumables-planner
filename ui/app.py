"""
Streamlit UI for the frac consumables planner.

This module provides a single-page Streamlit application with:

1. CONFIG PANEL (sidebar):
   - Sliders/inputs for all SimulationConfig parameters
   - [Generate] button to create new random data
   - [Load] button to load from file
   - [Export] button to save current data
   - [Reset] button to restore defaults

2. MAIN AREA:
   - Display of Crew A's pump status and needs
   - Table of nearby crews sorted by distance
   - [Generate Order Plan] button to invoke the agent
   - Agent recommendation display
   - Editable order form
   - [Approve & Order] confirmation button

Data Flow:
   Config → Generate → Session State → Display → Agent → Order Plan

Usage:
    streamlit run ui/app.py
"""

import streamlit as st


def main():
    """Main Streamlit application entry point."""
    # TODO: Implement Streamlit UI
    st.title("Frac Consumables Planner")
    st.write("Application skeleton - implementation pending")


if __name__ == "__main__":
    main()
