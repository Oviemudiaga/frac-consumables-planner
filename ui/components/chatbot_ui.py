"""
Chatbot UI component for the Streamlit application.

This module provides the chat interface that displays in the right panel
of both the Pump Status and Job Planning tabs.

Usage:
    from ui.components.chatbot_ui import render_chatbot

    render_chatbot(crew_data, context_mode="pump_status", order_plan=None)
"""

import streamlit as st

from schemas.crew import CrewData
from schemas.order import OrderPlan
from tools.needs_calculator import calculate_needs
from tools.inventory_reader import read_inventory
from tools.order_planner import plan_order
from ui.chatbot import (
    ChatMessage,
    build_pump_status_context,
    build_job_planning_context,
    create_chatbot_llm,
    generate_chat_response,
    generate_structured_chat_response,
)


def render_chatbot(
    crew_data: CrewData,
    context_mode: str,
    order_plan: OrderPlan | None = None,
    selected_model: str = "llama3"
):
    """
    Render the chatbot interface.

    Args:
        crew_data: Current crew data for context
        context_mode: "pump_status" or "job_planning"
        order_plan: Order plan if available (for job planning context)
        selected_model: Ollama model to use
    """
    st.subheader("Assistant")

    # Context indicator
    if context_mode == "pump_status":
        st.caption("Ask questions about pump status and fleet health")
    else:
        st.caption("Ask questions about job planning and orders")

    # Initialize chat history in session state if needed
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Chat container with scrollable history
    chat_container = st.container(height=400)

    with chat_container:
        if not st.session_state.chat_history:
            st.info("Ask me anything about your pump status or job planning!")
        else:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg.role):
                    st.markdown(msg.content)

    # Chat input
    if prompt := st.chat_input("Ask a question...", key=f"chat_input_{context_mode}"):
        # Add user message to history
        user_msg = ChatMessage(role="user", content=prompt)
        st.session_state.chat_history.append(user_msg)

        # Build context based on current tab
        if context_mode == "pump_status":
            system_prompt = build_pump_status_context(crew_data)
        else:
            # Generate order_plan if not provided (ensures consistent recommendations)
            if order_plan is None:
                crew_a = next((c for c in crew_data.crews if c.distance_to_crew_a is None), None)
                if crew_a:
                    needs = calculate_needs(crew_data, "A")
                    inventory = read_inventory(crew_data)
                    order_plan = plan_order(
                        needs=needs,
                        crew_a_spares=crew_a.spares,
                        nearby_crews=inventory["nearby_crews"],
                        crew_id=crew_a.crew_id,
                        job_duration_hours=crew_a.job_duration_hours
                    )
            system_prompt = build_job_planning_context(crew_data, order_plan)

        # Generate response
        with st.spinner("Thinking..."):
            try:
                llm = create_chatbot_llm(model=selected_model)
                # Use structured output for job planning to ensure consistent recommendations
                if context_mode == "job_planning":
                    response = generate_structured_chat_response(
                        llm=llm,
                        system_prompt=system_prompt,
                        chat_history=st.session_state.chat_history[:-1],
                        user_message=prompt,
                        order_plan=order_plan  # Pass order_plan for programmatic recommendations
                    )
                else:
                    response = generate_chat_response(
                        llm=llm,
                        system_prompt=system_prompt,
                        chat_history=st.session_state.chat_history[:-1],
                        user_message=prompt
                    )
            except Exception as e:
                response = f"Error connecting to Ollama: {str(e)}. Make sure Ollama is running with `ollama serve`."

        # Add assistant response to history
        assistant_msg = ChatMessage(role="assistant", content=response)
        st.session_state.chat_history.append(assistant_msg)

        st.rerun()

    # Clear chat button
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Clear Chat", use_container_width=True, key=f"clear_chat_{context_mode}"):
            st.session_state.chat_history = []
            st.rerun()
    with col2:
        st.caption(f"Model: {selected_model}")
