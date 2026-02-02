"""
Streamlit UI for consumables planning.

Single-page application that:
1. Accepts job parameters (pumps, hours)
2. Calls agent to generate order plan
3. Displays agent recommendation
4. Shows editable order form
5. Handles user approval

Layout:
  - Header with app title
  - Job parameters input form (sidebar)
  - Agent recommendation display
  - Order table (editable)
  - Approve & Order button
  - Confirmation message

State Management:
  - Session state for order plan
  - Editable dataframe for order quantities
  - Approval workflow
"""

import streamlit as st
from agent.orchestrator import run_planning_session
from schemas.order import OrderPlan


def main():
    """
    Main Streamlit application entry point.

    Flow:
        1. Display job parameters form
        2. User submits parameters
        3. Agent generates plan
        4. Display recommendation and editable order
        5. User approves
        6. Show confirmation
    """
    st.set_page_config(
        page_title="Frac Consumables Planner",
        page_icon="🔧",
        layout="wide"
    )

    st.title("🔧 Frac Consumables Planner")
    st.markdown("Plan consumable orders efficiently by borrowing from nearby crews")

    # Sidebar for job parameters
    with st.sidebar:
        st.header("Job Parameters")
        # Input fields will be added in Phase 4
        ...

    # Main area for results
    st.header("Order Recommendation")
    # Display logic will be added in Phase 4
    ...

    # Order form
    st.header("Order Details")
    # Editable table will be added in Phase 4
    ...

    # Approval button
    # Approval workflow will be added in Phase 4
    ...


if __name__ == "__main__":
    main()
