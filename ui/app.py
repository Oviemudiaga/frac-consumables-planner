"""
Streamlit UI for the frac consumables planner.

This module provides a tabbed Streamlit application with:

1. PUMP STATUS TAB:
   - Left panel: All crews' pump status with health indicators
   - Right panel: Context-aware chatbot for pump questions

2. JOB PLANNING TAB:
   - Left panel: Crew A's job planning and order generation
   - Right panel: Context-aware chatbot for planning questions

Usage:
    streamlit run ui/app.py
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.crew import CrewData
from schemas.config import SimulationConfig
from schemas.order import OrderPlan
from generator.data_generator import generate_crew_data, load_crew_data, save_crew_data
from agent.orchestrator import create_agent, run_agent
from ui.ollama_utils import get_available_models
from ui.components.pump_status import render_all_crews_status
from ui.components.chatbot_ui import render_chatbot


def get_available_scenarios() -> list[str]:
    """Get list of available scenario files."""
    examples_dir = Path(__file__).parent.parent / "data" / "examples"
    if examples_dir.exists():
        return [f.name for f in examples_dir.glob("*.json")]
    return []


def get_crew_a(crew_data: CrewData):
    """Get Crew A (the crew with distance_to_crew_a = None)."""
    for crew in crew_data.crews:
        if crew.distance_to_crew_a is None:
            return crew
    return None



def initialize_session_state():
    """Initialize all session state variables."""
    if "crew_data" not in st.session_state:
        default_path = Path(__file__).parent.parent / "data" / "examples" / "scenario_3crews.json"
        st.session_state.crew_data = load_crew_data(str(default_path))
    if "show_order_plan" not in st.session_state:
        st.session_state.show_order_plan = False
    if "order_approved" not in st.session_state:
        st.session_state.order_approved = False
    if "order_quantities" not in st.session_state:
        st.session_state.order_quantities = {}
    if "agent_result" not in st.session_state:
        st.session_state.agent_result = None
    if "agent_error" not in st.session_state:
        st.session_state.agent_error = None
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = "llama3"
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "pump_status"
    # Weather seed for stable weather within a session
    if "weather_seed" not in st.session_state:
        st.session_state.weather_seed = 42


def render_settings_panel():
    """Render the collapsible settings panel."""
    crew_data = st.session_state.crew_data

    with st.expander("Settings & Data Management", expanded=False):
        st.markdown("#### Data Loading")
        data_col1, data_col2, data_col3 = st.columns(3)

        with data_col1:
            scenarios = get_available_scenarios()
            selected_scenario = st.selectbox(
                "Select Scenario",
                options=scenarios,
                index=scenarios.index("scenario_3crews.json") if "scenario_3crews.json" in scenarios else 0
            )
            if st.button("Load from File", use_container_width=True):
                try:
                    filepath = Path(__file__).parent.parent / "data" / "examples" / selected_scenario
                    st.session_state.crew_data = load_crew_data(str(filepath))
                    st.session_state.show_order_plan = False
                    st.session_state.order_approved = False
                    st.session_state.order_quantities = {}
                    st.session_state.agent_result = None
                    st.session_state.agent_error = None
                    st.session_state.chat_history = []
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to load file: {e}")

        with data_col2:
            export_filename = st.text_input("Export Filename", value="exported_data.json")
            if st.button("Export Data", use_container_width=True):
                try:
                    export_path = Path(__file__).parent.parent / "data" / export_filename
                    save_crew_data(st.session_state.crew_data, str(export_path))
                    st.success(f"Data exported to {export_path}")
                except Exception as e:
                    st.error(f"Failed to export: {e}")

        with data_col3:
            st.caption("Generate new random data")
            if st.button("Generate New Data", use_container_width=True):
                st.session_state.show_generator = True
            if st.button("Reset Session", use_container_width=True, type="secondary"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

        st.divider()

        # Generation Settings
        if st.session_state.get("show_generator", False):
            st.markdown("#### Generation Settings")
            gen_col1, gen_col2, gen_col3 = st.columns(3)

            with gen_col1:
                num_crews = st.slider("Number of Crews", min_value=2, max_value=10, value=3)
                min_pumps = st.slider("Min Pumps per Crew", min_value=1, max_value=6, value=2)
                max_pumps = st.slider("Max Pumps per Crew", min_value=2, max_value=8, value=5)

            with gen_col2:
                min_job = st.slider("Min Job Duration (hrs)", min_value=20, max_value=80, value=40)
                max_job = st.slider("Max Job Duration (hrs)", min_value=40, max_value=120, value=70)
                proximity = st.slider("Proximity Threshold (mi)", min_value=5.0, max_value=50.0, value=10.0)

            with gen_col3:
                consumables_per = st.slider("Consumables per Pump", min_value=1, max_value=10, value=5)
                seed_input = st.text_input("Random Seed (optional)", value="")
                seed_value = int(seed_input) if seed_input.strip().isdigit() else None

            if st.button("Generate", type="primary", use_container_width=True):
                try:
                    config = SimulationConfig(
                        num_crews=num_crews,
                        min_pumps_per_crew=min_pumps,
                        max_pumps_per_crew=max_pumps,
                        min_job_duration=min_job,
                        max_job_duration=max_job,
                        proximity_threshold_miles=proximity,
                        consumables_per_pump=consumables_per,
                        seed=seed_value
                    )
                    st.session_state.crew_data = generate_crew_data(config)
                    st.session_state.show_order_plan = False
                    st.session_state.order_approved = False
                    st.session_state.order_quantities = {}
                    st.session_state.agent_result = None
                    st.session_state.agent_error = None
                    st.session_state.chat_history = []
                    st.session_state.show_generator = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Generation failed: {e}")
        else:
            st.markdown("#### Current Data Info")
            st.info(f"Loaded: {len(crew_data.crews)} crews, Proximity threshold: {crew_data.proximity_threshold_miles} mi, "
                    f"Consumables per pump: {crew_data.consumables_per_pump}")

        st.divider()

        # LLM Model Settings
        st.markdown("#### LLM Settings")
        model_col1, model_col2 = st.columns([2, 1])

        with model_col1:
            models = get_available_models()
            if models:
                default_idx = models.index(st.session_state.selected_model) if st.session_state.selected_model in models else 0
                st.session_state.selected_model = st.selectbox(
                    "Ollama Model",
                    options=models,
                    index=default_idx
                )
            else:
                st.warning("No Ollama models found. Run: `ollama pull llama3`")
                st.session_state.selected_model = "llama3"

        with model_col2:
            st.caption("Refresh list")
            if st.button("Refresh Models", use_container_width=True):
                st.rerun()


def render_pump_status_tab():
    """Render the Pump Status tab content."""
    crew_data = st.session_state.crew_data

    left_col, right_col = st.columns([3, 2])

    with left_col:
        render_all_crews_status(crew_data)

    with right_col:
        # Pass order_plan so intent routing works on pump_status tab too
        order_plan = st.session_state.agent_result.get("order_plan") if st.session_state.agent_result else None
        render_chatbot(
            crew_data=crew_data,
            context_mode="pump_status",
            order_plan=order_plan,
            selected_model=st.session_state.selected_model
        )


def render_job_planning_tab():
    """Render the Job Planning tab content."""
    crew_data = st.session_state.crew_data

    left_col, right_col = st.columns([3, 2])

    with left_col:
        render_order_plan_section(crew_data)

    with right_col:
        order_plan = st.session_state.agent_result.get("order_plan") if st.session_state.agent_result else None
        render_chatbot(
            crew_data=crew_data,
            context_mode="job_planning",
            order_plan=order_plan,
            selected_model=st.session_state.selected_model
        )


def render_order_plan_section(crew_data: CrewData):
    """Render the order plan generation and display section."""
    st.subheader("Order Plan")

    # Generate Order Plan button
    btn_col1, btn_col2 = st.columns([3, 1])
    with btn_col1:
        generate_clicked = st.button("Generate Order Plan", type="primary", use_container_width=True)
    with btn_col2:
        if st.session_state.show_order_plan:
            if st.button("Cancel", use_container_width=True):
                st.session_state.show_order_plan = False
                st.session_state.order_approved = False
                st.session_state.order_quantities = {}
                st.session_state.agent_result = None
                st.session_state.agent_error = None
                st.rerun()

    # Handle Generate button click
    if generate_clicked:
        st.session_state.agent_error = None
        st.session_state.order_approved = False

        with st.spinner("Agent is analyzing data and generating order plan..."):
            try:
                agent = create_agent(model=st.session_state.selected_model)
                result = run_agent(agent, crew_data, weather_seed=st.session_state.weather_seed)
                st.session_state.agent_result = result
                st.session_state.show_order_plan = True

                # Initialize order quantities from the plan
                order_plan: OrderPlan = result["order_plan"]
                st.session_state.order_quantities = {
                    item.consumable_name: item.to_order for item in order_plan.items
                }
            except Exception as e:
                st.session_state.agent_error = str(e)
                st.session_state.show_order_plan = False

        st.rerun()

    # Display agent error if any
    if st.session_state.agent_error:
        st.error(f"Agent failed: {st.session_state.agent_error}")
        st.info(f"Make sure Ollama is running with the {st.session_state.selected_model} model: `ollama pull {st.session_state.selected_model} && ollama serve`")

    # Display order plan if available
    if st.session_state.show_order_plan and st.session_state.agent_result:
        result = st.session_state.agent_result
        order_plan: OrderPlan = result["order_plan"]
        cost_summary = result.get("cost_summary")

        display_names = {
            "valve_packings": "Valve Packings",
            "seals": "Seals",
            "plungers": "Plungers"
        }

        # Consolidated order + cost table
        st.markdown("#### Order Summary")
        table_rows = []
        for item in order_plan.items:
            name = display_names.get(item.consumable_name, item.consumable_name)
            item_cost = cost_summary["items"].get(item.consumable_name, {}) if cost_summary else {}

            # Borrow source info
            if item.borrow_sources:
                borrow_qty = sum(b.quantity for b in item.borrow_sources)
                borrow_source = ", ".join(f"Crew {b.crew_id}" for b in item.borrow_sources)
            else:
                borrow_qty = 0
                borrow_source = "-"

            # Cost columns
            borrow_cpu = item_cost.get("borrow_cost_per_unit")
            order_cpu = item_cost.get("order_cost_per_unit")
            action = item_cost.get("action", "none_needed")

            # Weather info
            weather_str = "-"
            if item.borrow_sources and cost_summary and cost_summary.get("weather"):
                parts = []
                for source in item.borrow_sources:
                    w = cost_summary["weather"].get(source.crew_id, {})
                    if w:
                        cond = w["condition"].replace("_", " ").title()
                        mult = w["multiplier"]
                        parts.append(f"{cond} ({mult}x)" if mult > 1.0 else cond)
                if parts:
                    weather_str = ", ".join(parts)

            decision_map = {"borrow": "BORROW", "order": "ORDER", "mixed": "MIXED", "none_needed": "OK"}

            table_rows.append({
                "Consumable": name,
                "Needed": item.total_needed,
                "On Hand": item.on_hand,
                "Borrow": borrow_qty,
                "Source": borrow_source,
                "Order": item.to_order,
                "Borrow $/unit": f"${borrow_cpu:.2f}" if borrow_cpu is not None else "-",
                "Order $/unit": f"${order_cpu:.2f}" if order_cpu is not None else "-",
                "Decision": decision_map.get(action, action.upper()),
                "Weather": weather_str,
            })

        df_order = pd.DataFrame(table_rows)
        st.dataframe(df_order, use_container_width=True, hide_index=True)

        # Total cost summary
        if cost_summary:
            st.markdown("#### Estimated Total Cost")
            cost_col1, cost_col2, cost_col3 = st.columns(3)
            with cost_col1:
                st.metric("Recommended Plan", f"${cost_summary['total_estimated_cost']:.2f}")
            with cost_col2:
                st.metric("If All Ordered", f"${cost_summary['total_if_all_ordered']:.2f}")
            with cost_col3:
                savings = cost_summary["total_savings"]
                if cost_summary["total_if_all_ordered"] > 0:
                    savings_pct = (savings / cost_summary["total_if_all_ordered"]) * 100
                    st.metric("Savings", f"${savings:.2f}", delta=f"{savings_pct:.1f}%")
                else:
                    st.metric("Savings", "$0.00")

        st.divider()

        # Editable order quantities
        st.markdown("#### Adjust Order Quantities")
        edit_cols = st.columns(len(order_plan.items))
        for i, item in enumerate(order_plan.items):
            with edit_cols[i]:
                name = display_names.get(item.consumable_name, item.consumable_name)
                new_qty = st.number_input(
                    name,
                    min_value=0,
                    value=st.session_state.order_quantities.get(item.consumable_name, item.to_order),
                    key=f"order_{item.consumable_name}",
                )
                st.session_state.order_quantities[item.consumable_name] = new_qty

        # Approve & Order button
        if st.button("Approve & Order", type="primary", use_container_width=True):
            st.session_state.order_approved = True
            st.rerun()

        if st.session_state.order_approved:
            st.success("Order approved and submitted successfully.")


def main():
    """Main Streamlit application entry point."""
    st.set_page_config(
        page_title="Frac Consumables Planner",
        page_icon="🔧",
        layout="wide"
    )

    st.title("Frac Consumables Planner")

    # Initialize session state
    initialize_session_state()

    # Render shared settings panel
    render_settings_panel()

    st.divider()

    # Create tabs
    tab1, tab2 = st.tabs([
        "📊 Pump Status",
        "📋 Job Planning",
    ])

    with tab1:
        st.session_state.active_tab = "pump_status"
        render_pump_status_tab()

    with tab2:
        st.session_state.active_tab = "job_planning"
        render_job_planning_tab()


if __name__ == "__main__":
    main()
