"""
Test script for the 5-crew stress test scenario.
"""

import json
from pathlib import Path
from schemas.crew import CrewData
from tools.needs_calculator import calculate_needs
from tools.inventory_reader import read_inventory
from tools.order_planner import plan_order


def main():
    # Load the 5-crew scenario data
    data_path = Path("data/examples/scenario_5crews.json")
    with open(data_path, "r") as f:
        raw_data = json.load(f)

    crew_data = CrewData(**raw_data)

    print("=" * 70)
    print("FRAC CONSUMABLES PLANNER - 5-CREW STRESS TEST")
    print("=" * 70)

    # Calculate needs for Crew A
    print("\n[1] Calculating needs for Crew A...")
    needs = calculate_needs(crew_data, "A")
    crew_a = [c for c in crew_data.crews if c.crew_id == "A"][0]
    print(f"Crew A job duration: {crew_a.job_duration_hours} hours")
    print(f"Crew A has {len(crew_a.pumps)} pumps")
    print(f"Consumables per pump: {crew_data.consumables_per_pump}")
    print("\nNeeds:")
    for consumable, data in needs.items():
        print(f"  - {consumable}: {data['pumps_needing']}/{len(crew_a.pumps)} pumps needing, "
              f"{data['total_needed']} total needed")

    # Read inventory
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
        print(f"\n  Crew {crew['crew_id']} @ {crew['distance']} miles:")
        print(f"    Available: VP={crew['available']['valve_packings']}, "
              f"S={crew['available']['seals']}, P={crew['available']['plungers']}")

    excluded = [c for c in crew_data.crews if c.distance_to_crew_a and c.distance_to_crew_a > crew_data.proximity_threshold_miles]
    if excluded:
        print(f"\nExcluded crews (beyond {crew_data.proximity_threshold_miles} miles):")
        for crew in excluded:
            print(f"  - Crew {crew.crew_id} @ {crew.distance_to_crew_a} miles")

    # Plan the order
    print("\n[3] Planning order with N-crew accumulation logic...")
    order_plan = plan_order(
        needs=needs,
        crew_a_spares=crew_a_spares,
        nearby_crews=nearby_crews,
        crew_id="A",
        job_duration_hours=crew_a.job_duration_hours
    )

    print(f"\n{'=' * 70}")
    print(f"ORDER PLAN FOR CREW {order_plan.crew_id}")
    print(f"{'=' * 70}")

    for item in order_plan.items:
        print(f"\n{item.consumable_name.upper()}:")
        print(f"  Pumps needing: {item.pumps_needing}")
        print(f"  Total needed:  {item.total_needed}")
        print(f"  On hand:       {item.on_hand}")
        print(f"  Shortfall:     {max(0, item.total_needed - item.on_hand)}")

        if item.borrow_sources:
            print(f"  Borrow plan:")
            total_borrowed = 0
            for borrow in item.borrow_sources:
                print(f"    -> Crew {borrow.crew_id}: {borrow.quantity} units ({borrow.distance} miles)")
                total_borrowed += borrow.quantity
            print(f"  Total borrowed: {total_borrowed}")

        if item.to_order > 0:
            print(f"  [!] MUST ORDER: {item.to_order} units from supplier")
        else:
            print(f"  [OK] No order needed")

    print("\n" + "=" * 70)
    print("STRESS TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
