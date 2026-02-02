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
from ui.chatbot import ChatMessage, handle_chat_message
from agent.intent_router import ChatIntent


def render_chatbot(
    crew_data: CrewData,
    context_mode: str,
    order_plan: OrderPlan | None = None,
    selected_model: str = "llama3",
    cost_summary: dict | None = None,
):
    """
    Render the chatbot interface.

    Args:
        crew_data: Current crew data for context
        context_mode: "pump_status" or "job_planning"
        order_plan: Order plan if available (for job planning context)
        selected_model: Ollama model to use
        cost_summary: Cost metadata from agent result (for job planning context)
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

        # Route through intent classifier
        with st.spinner("Thinking..."):
            try:
                response, intent = handle_chat_message(
                    crew_data=crew_data,
                    user_message=prompt,
                    chat_history=st.session_state.chat_history[:-1],
                    order_plan=order_plan,
                    selected_model=selected_model,
                    context_mode=context_mode,
                    cost_summary=cost_summary,
                )

                # Add intent badge for order/cost/explain responses
                if intent == ChatIntent.ORDER:
                    response = "**[Order Plan]**\n\n" + response
                elif intent == ChatIntent.COST:
                    response = "**[Cost Analysis]**\n\n" + response
                elif intent == ChatIntent.EXPLAIN:
                    response = "**[Analysis]**\n\n" + response
            except Exception as e:
                response = f"Error: {str(e)}. Make sure Ollama is running with `ollama serve`."

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
