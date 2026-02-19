"""
Pump status display components for the Streamlit UI.

This module provides components to display pump health status
for all crews with color-coded indicators.

Usage:
    from ui.components.pump_status import render_all_crews_status

    render_all_crews_status(crew_data)
"""

import pandas as pd
import streamlit as st

from schemas.crew import CrewData, Crew
from tools.inventory_reader import read_inventory


def get_crew_geography(crew: Crew) -> tuple[str, str, str]:
    """
    Safely get geography attributes with fallbacks for old data.

    Args:
        crew: Crew object

    Returns:
        Tuple of (country, region, area) with defaults if not present
    """
    country = getattr(crew, 'country', 'United States')
    region = getattr(crew, 'region', 'Texas')
    area = getattr(crew, 'area', 'Permian Basin')
    return country, region, area


def get_health_color(remaining_life: int, job_duration: int) -> str:
    """
    Get CSS color based on health status.

    Args:
        remaining_life: Hours remaining for consumable
        job_duration: Job duration in hours

    Returns:
        CSS color string
    """
    if job_duration == 0:
        return "#28a745"  # Green

    ratio = remaining_life / job_duration
    if ratio >= 1.5:
        return "#28a745"  # Green - healthy
    elif ratio >= 1.0:
        return "#ffc107"  # Yellow - marginal
    else:
        return "#dc3545"  # Red - critical


def get_health_emoji(remaining_life: int, job_duration: int) -> str:
    """
    Get emoji indicator based on health status.

    Args:
        remaining_life: Hours remaining for consumable
        job_duration: Job duration in hours

    Returns:
        Emoji string
    """
    if job_duration == 0:
        return "🟢"

    ratio = remaining_life / job_duration
    if ratio >= 1.5:
        return "🟢"
    elif ratio >= 1.0:
        return "🟡"
    else:
        return "🔴"


def render_crew_pump_card(crew: Crew, consumables_per_pump: int):
    """
    Render a card showing one crew's pump status and spares.

    Args:
        crew: Crew object
        consumables_per_pump: Number of consumables needed per pump
    """
    # Determine if this is Crew A
    is_crew_a = crew.distance_to_crew_a is None
    distance_str = " (Primary)" if is_crew_a else f" — {crew.distance_to_crew_a} mi"

    with st.container(border=True):
        # Header with location
        country, region, area = get_crew_geography(crew)
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### Crew {crew.crew_id}{distance_str}")
            st.caption(f"📍 {area}, {region}, {country}")
        with col2:
            st.metric("Job", f"{crew.job_duration_hours}h")

        # Pump status table
        st.caption(f"Pump Status (job duration: {crew.job_duration_hours}h)")

        pump_data = []
        for pump in crew.pumps:
            vp_emoji = get_health_emoji(pump.valve_packings_life, crew.job_duration_hours)
            seals_emoji = get_health_emoji(pump.seals_life, crew.job_duration_hours)
            plungers_emoji = get_health_emoji(pump.plungers_life, crew.job_duration_hours)

            pump_data.append({
                "Pump": f"#{pump.pump_id}",
                "VP": f"{pump.valve_packings_life}h {vp_emoji}",
                "Seals": f"{pump.seals_life}h {seals_emoji}",
                "Plungers": f"{pump.plungers_life}h {plungers_emoji}"
            })

        df = pd.DataFrame(pump_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Spares
        st.caption("Spares Inventory")
        sp_col1, sp_col2, sp_col3 = st.columns(3)
        with sp_col1:
            st.metric("VP", crew.spares.valve_packings)
        with sp_col2:
            st.metric("Seals", crew.spares.seals)
        with sp_col3:
            st.metric("Plungers", crew.spares.plungers)


def render_all_crews_status(crew_data: CrewData):
    """
    Render pump status for all crews with health indicators.

    Args:
        crew_data: CrewData containing all crew information
    """
    st.subheader("Fleet Pump Status")

    # Sort crews: Crew A first, then by distance
    sorted_crews = sorted(
        crew_data.crews,
        key=lambda c: (0 if c.distance_to_crew_a is None else 1, c.distance_to_crew_a or 0)
    )

    # ---- Geographic Cascading Filters ----
    # Build geography lookup for all crews (handles old data without geography)
    crew_geographies = {c.crew_id: get_crew_geography(c) for c in crew_data.crews}

    st.markdown("##### Filter by Location")
    geo_col1, geo_col2, geo_col3 = st.columns(3)

    # Country filter
    all_countries = sorted(set(geo[0] for geo in crew_geographies.values()))
    with geo_col1:
        selected_country = st.selectbox(
            "Country",
            options=["All"] + all_countries,
            key="country_filter"
        )

    # Region filter (cascaded based on country)
    if selected_country == "All":
        available_regions = sorted(set(geo[1] for geo in crew_geographies.values()))
    else:
        available_regions = sorted(set(geo[1] for geo in crew_geographies.values() if geo[0] == selected_country))

    with geo_col2:
        selected_region = st.selectbox(
            "Region",
            options=["All"] + available_regions,
            key="region_filter"
        )

    # Area filter (cascaded based on region)
    if selected_country == "All" and selected_region == "All":
        available_areas = sorted(set(geo[2] for geo in crew_geographies.values()))
    elif selected_region == "All":
        available_areas = sorted(set(geo[2] for geo in crew_geographies.values() if geo[0] == selected_country))
    else:
        available_areas = sorted(set(geo[2] for geo in crew_geographies.values()
                                     if (selected_country == "All" or geo[0] == selected_country)
                                     and geo[1] == selected_region))

    with geo_col3:
        selected_area = st.selectbox(
            "Area",
            options=["All"] + available_areas,
            key="area_filter"
        )

    # Apply geographic filters using the lookup
    geo_filtered_crews = sorted_crews
    if selected_country != "All":
        geo_filtered_crews = [c for c in geo_filtered_crews if crew_geographies[c.crew_id][0] == selected_country]
    if selected_region != "All":
        geo_filtered_crews = [c for c in geo_filtered_crews if crew_geographies[c.crew_id][1] == selected_region]
    if selected_area != "All":
        geo_filtered_crews = [c for c in geo_filtered_crews if crew_geographies[c.crew_id][2] == selected_area]

    # ---- Crew Selector (within geographic filter) ----
    all_crew_ids = [crew.crew_id for crew in geo_filtered_crews]

    selected_crew_ids = st.multiselect(
        "Select Crews to Display",
        options=all_crew_ids,
        default=all_crew_ids,
        key="crew_filter",
        help="Filter which crews to show in the view below"
    )

    # Filter crews based on selection
    filtered_crews = [c for c in geo_filtered_crews if c.crew_id in selected_crew_ids]

    # Summary metrics (based on filtered crews)
    total_pumps = sum(len(crew.pumps) for crew in filtered_crews)
    critical_count = 0
    for crew in filtered_crews:
        for pump in crew.pumps:
            if (pump.valve_packings_life < crew.job_duration_hours or
                pump.seals_life < crew.job_duration_hours or
                pump.plungers_life < crew.job_duration_hours):
                critical_count += 1

    # Fleet overview
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    with metric_col1:
        st.metric("Crews Shown", f"{len(filtered_crews)}/{len(crew_data.crews)}")
    with metric_col2:
        st.metric("Total Pumps", total_pumps)
    with metric_col3:
        st.metric("Pumps Critical", critical_count, delta=None if critical_count == 0 else f"-{critical_count}", delta_color="inverse")
    with metric_col4:
        st.metric("Proximity", f"{crew_data.proximity_threshold_miles} mi")

    st.divider()

    # Health legend
    st.caption("🟢 Healthy (>1.5x job duration) | 🟡 Marginal (1-1.5x) | 🔴 Critical (<1x)")

    # Render each filtered crew in a scrollable container
    if not filtered_crews:
        st.info("No crews selected. Use the filter above to select crews to display.")
    else:
        with st.container(height=600):
            for crew in filtered_crews:
                render_crew_pump_card(crew, crew_data.consumables_per_pump)

            # Nearby crews available spares
            st.divider()
            st.markdown("#### Nearby Crews — Available for Crew A")
            st.caption(f"Within {crew_data.proximity_threshold_miles} miles (after their own needs)")

            inventory = read_inventory(crew_data)
            if not inventory["nearby_crews"]:
                st.info("No nearby crews within proximity threshold")
            else:
                nearby_rows = []
                for nearby in inventory["nearby_crews"]:
                    nearby_crew = next((c for c in crew_data.crews if c.crew_id == nearby["crew_id"]), None)
                    area = getattr(nearby_crew, "area", "") if nearby_crew else ""
                    nearby_rows.append({
                        "Crew": nearby["crew_id"],
                        "Distance (mi)": nearby["distance"],
                        "Area": area,
                        "Valve Packings": nearby["available"]["valve_packings"],
                        "Seals": nearby["available"]["seals"],
                        "Plungers": nearby["available"]["plungers"],
                    })
                df_nearby = pd.DataFrame(nearby_rows)
                st.dataframe(df_nearby, use_container_width=True, hide_index=True)
