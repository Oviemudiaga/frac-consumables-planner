"""
Streamlit UI for the frac consumables planner.

This module provides a single-page Streamlit application with:

1. CONFIG PANEL (collapsible expander):
   - Sliders/inputs for simulation parameters
   - Load/Generate/Export data buttons

2. MAIN AREA:
   - Left column: Crew A's pump status and needs
   - Right column: Nearby crews sorted by distance
   - Order plan section with editable form

Usage:
    streamlit run ui/app.py
"""

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.crew import CrewData
from schemas.config import SimulationConfig
from schemas.order import OrderPlan
from tools.needs_calculator import calculate_needs
from tools.inventory_reader import read_inventory
from generator.data_generator import generate_crew_data, load_crew_data, save_crew_data
from agent.orchestrator import create_agent, run_agent
from ui.ollama_utils import get_available_models


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


def get_status_indicator(remaining_life: int, job_duration: int) -> str:
    """Return status indicator based on remaining life vs job duration."""
    if remaining_life >= job_duration:
        return "✓"
    return "⚠️"


def style_pump_table(df: pd.DataFrame, job_duration: int) -> pd.DataFrame:
    """Apply styling to highlight cells where life < job_duration."""
    def highlight_low_life(val, col_name):
        if col_name in ["Valve Packings", "Seals", "Plungers"]:
            if isinstance(val, (int, float)) and val < job_duration:
                return "background-color: #ffcccc; color: #cc0000; font-weight: bold"
        return ""

    styled = df.style.apply(
        lambda row: [highlight_low_life(val, col) for col, val in row.items()],
        axis=1
    )
    return styled


def main():
    """Main Streamlit application entry point."""
    st.set_page_config(
        page_title="Frac Consumables Planner",
        page_icon="🔧",
        layout="wide"
    )

    st.title("Frac Consumables Planner")

    # Initialize session state
    if "crew_data" not in st.session_state:
        # Load default scenario
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

    crew_data = st.session_state.crew_data
    crew_a = get_crew_a(crew_data)

    # Collapsible Simulation Settings Panel
    with st.expander("Simulation Settings & Data Management", expanded=False):
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

    st.divider()

    # Refresh data reference after potential changes
    crew_data = st.session_state.crew_data
    crew_a = get_crew_a(crew_data)

    # Main content: Two columns
    left_col, right_col = st.columns([3, 2])

    # LEFT COLUMN: Crew A Details
    with left_col:
        st.subheader(f"Crew {crew_a.crew_id} - Job Plan")
        st.metric("Job Duration", f"{crew_a.job_duration_hours} hours")

        # Pump Status Table
        st.markdown("#### Pump Status")
        st.caption(f"⚠️ = remaining life < job duration ({crew_a.job_duration_hours} hrs) | ✓ = sufficient")

        pump_data = []
        for pump in crew_a.pumps:
            pump_data.append({
                "Pump #": pump.pump_id,
                "Valve Packings": f"{pump.valve_packings_life} {get_status_indicator(pump.valve_packings_life, crew_a.job_duration_hours)}",
                "Seals": f"{pump.seals_life} {get_status_indicator(pump.seals_life, crew_a.job_duration_hours)}",
                "Plungers": f"{pump.plungers_life} {get_status_indicator(pump.plungers_life, crew_a.job_duration_hours)}"
            })

        df_pumps = pd.DataFrame(pump_data)
        st.dataframe(df_pumps, use_container_width=True, hide_index=True)

        # Spares On Hand
        st.markdown("#### Spares On Hand")
        spares_col1, spares_col2, spares_col3 = st.columns(3)
        with spares_col1:
            st.metric("Valve Packings", crew_a.spares.valve_packings)
        with spares_col2:
            st.metric("Seals", crew_a.spares.seals)
        with spares_col3:
            st.metric("Plungers", crew_a.spares.plungers)

        # Calculated Needs
        st.markdown("#### Calculated Needs")
        needs = calculate_needs(crew_data, "A")

        needs_data = []
        for consumable, data in needs.items():
            display_name = consumable.replace("_", " ").title()
            status = "⚠️ Needs attention" if data["total_needed"] > 0 else "✓ OK"
            needs_data.append({
                "Consumable": display_name,
                "Pumps Needing": data["pumps_needing"],
                "Total Needed": data["total_needed"],
                "Status": status
            })

        df_needs = pd.DataFrame(needs_data)
        st.dataframe(df_needs, use_container_width=True, hide_index=True)

    # RIGHT COLUMN: Nearby Crews
    with right_col:
        st.subheader("Nearby Crews")
        st.caption(f"Within {crew_data.proximity_threshold_miles} miles")

        inventory = read_inventory(crew_data)

        if not inventory["nearby_crews"]:
            st.info("No nearby crews within proximity threshold")
        else:
            for nearby in inventory["nearby_crews"]:
                with st.container(border=True):
                    st.markdown(f"**Crew {nearby['crew_id']}** — {nearby['distance']} miles")
                    st.caption("Available Spares (after their own needs)")

                    avail_col1, avail_col2, avail_col3 = st.columns(3)
                    with avail_col1:
                        val = nearby["available"]["valve_packings"]
                        st.metric("Valve Packings", f"{val} {'✓' if val > 0 else ''}")
                    with avail_col2:
                        val = nearby["available"]["seals"]
                        st.metric("Seals", f"{val} {'✓' if val > 0 else ''}")
                    with avail_col3:
                        val = nearby["available"]["plungers"]
                        st.metric("Plungers", f"{val} {'✓' if val > 0 else ''}")

    st.divider()

    # Order Plan Section
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
                result = run_agent(agent, crew_data)
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

        # Agent Recommendation
        st.markdown("#### Agent Recommendation")
        with st.container(border=True):
            st.markdown(result["recommendation"])

        st.markdown("#### Order Details")

        display_names = {
            "valve_packings": "Valve Packings",
            "seals": "Seals",
            "plungers": "Plungers"
        }

        # Display order table with editable quantities
        for item in order_plan.items:
            with st.container(border=True):
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 2, 1])

                with col1:
                    status = "⚠️" if item.pumps_needing > 0 else "✓"
                    st.markdown(f"**{display_names.get(item.consumable_name, item.consumable_name)}** {status}")
                    st.caption(f"{item.pumps_needing} pumps need replacement")

                with col2:
                    st.metric("Needed", item.total_needed)

                with col3:
                    st.metric("On Hand", item.on_hand)

                with col4:
                    if item.borrow_sources:
                        total_borrowed = sum(b.quantity for b in item.borrow_sources)
                        borrow_text = ", ".join([
                            f"Crew {b.crew_id}: {b.quantity} ({b.distance}mi)"
                            for b in item.borrow_sources
                        ])
                        st.metric("Borrow", total_borrowed)
                        st.caption(borrow_text)
                    else:
                        st.metric("Borrow", 0)
                        st.caption("None available")

                with col5:
                    new_qty = st.number_input(
                        "Order",
                        min_value=0,
                        value=st.session_state.order_quantities.get(item.consumable_name, item.to_order),
                        key=f"order_{item.consumable_name}",
                        label_visibility="visible"
                    )
                    st.session_state.order_quantities[item.consumable_name] = new_qty

        st.divider()

        # Approve & Order button
        approve_col1, approve_col2 = st.columns([1, 1])
        with approve_col1:
            if st.button("Approve & Order", type="primary", use_container_width=True):
                st.session_state.order_approved = True
                st.rerun()

        if st.session_state.order_approved:
            st.success("Order sent! Order approved and submitted successfully.")

            # Show summary
            st.markdown("#### Order Summary")
            summary_data = []
            for consumable, qty in st.session_state.order_quantities.items():
                if qty > 0:
                    summary_data.append({
                        "Consumable": display_names.get(consumable, consumable.replace("_", " ").title()),
                        "Quantity Ordered": qty
                    })

            if summary_data:
                st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
            else:
                st.info("No items ordered - all needs can be met from on-hand spares and borrowing.")

            # Borrow Summary
            st.markdown("#### Borrow Summary")
            borrow_data = []
            for item in order_plan.items:
                for source in item.borrow_sources:
                    borrow_data.append({
                        "Consumable": display_names.get(item.consumable_name, item.consumable_name),
                        "From Crew": source.crew_id,
                        "Quantity": source.quantity,
                        "Distance (mi)": source.distance
                    })

            if borrow_data:
                st.dataframe(pd.DataFrame(borrow_data), use_container_width=True, hide_index=True)
            else:
                st.info("No borrowing required.")


if __name__ == "__main__":
    main()
