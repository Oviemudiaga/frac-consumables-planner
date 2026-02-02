"""
Test script to verify end-to-end flow of the three core tools.

This script:
1. Loads scenario_3crews.json
2. Calls calculate_needs to get Crew A's needs
3. Calls read_inventory to get spares and nearby crews
4. Calls plan_order to generate the order plan
5. Prints the results
"""

import json
from pathlib import Path
from schemas.crew import CrewData
from tools.needs_calculator import calculate_needs
from tools.inventory_reader import read_inventory
from tools.order_planner import plan_order


def main():
    # Load the scenario data
    data_path = Path("data/examples/scenario_3crews.json")
    with open(data_path, "r") as f:
        raw_data = json.load(f)

    # Parse into CrewData model
    crew_data = CrewData(**raw_data)

    print("=" * 60)
    print("FRAC CONSUMABLES PLANNER - TEST FLOW")
    print("=" * 60)

    # Step 1: Calculate needs for Crew A
    print("\n[1] Calculating needs for Crew A...")
    needs = calculate_needs(crew_data, "A")
    print(f"Crew A job duration: {crew_data.crews[0].job_duration_hours} hours")
    print(f"Consumables per pump: {crew_data.consumables_per_pump}")
    print("\nNeeds:")
    for consumable, data in needs.items():
        print(f"  - {consumable}: {data['pumps_needing']} pumps needing, "
              f"{data['total_needed']} total needed")

    # Step 2: Read inventory
    print("\n[2] Reading inventory...")
    inventory = read_inventory(crew_data)
    crew_a_spares = inventory["crew_a_spares"]
    nearby_crews = inventory["nearby_crews"]

    print(f"\nCrew A spares on hand:")
    print(f"  - valve_packings: {crew_a_spares.valve_packings}")
    print(f"  - seals: {crew_a_spares.seals}")
    print(f"  - plungers: {crew_a_spares.plungers}")

    print(f"\nNearby crews (within {crew_data.proximity_threshold_miles} miles):")
    for crew in nearby_crews:
        print(f"  - Crew {crew['crew_id']} ({crew['distance']} miles)")
        print(f"    Available: valve_packings={crew['available']['valve_packings']}, "
              f"seals={crew['available']['seals']}, plungers={crew['available']['plungers']}")

    # Step 3: Plan the order
    print("\n[3] Planning order...")
    order_plan = plan_order(
        needs=needs,
        crew_a_spares=crew_a_spares,
        nearby_crews=nearby_crews,
        crew_id="A",
        job_duration_hours=crew_data.crews[0].job_duration_hours
    )

    print(f"\nOrder Plan for Crew {order_plan.crew_id}:")
    print(f"Job duration: {order_plan.job_duration_hours} hours")
    print("\nOrder Details:")

    for item in order_plan.items:
        print(f"\n  {item.consumable_name.upper()}:")
        print(f"    Pumps needing: {item.pumps_needing}")
        print(f"    Total needed: {item.total_needed}")
        print(f"    On hand: {item.on_hand}")

        if item.borrow_sources:
            print(f"    Borrow from:")
            for borrow in item.borrow_sources:
                print(f"      - Crew {borrow.crew_id}: {borrow.quantity} units ({borrow.distance} miles)")

        if item.to_order > 0:
            print(f"    TO ORDER: {item.to_order} units")
        else:
            print(f"    No order needed")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
