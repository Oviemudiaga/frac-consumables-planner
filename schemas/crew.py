"""
Pydantic models for crew and consumable inventory data.

Defines:
- Consumable: Represents a single consumable item (valve packing, seal, valve)
  with quantity, remaining life hours, and surplus.
- Crew: Represents a frac crew with ID, pump count, distance, and inventory list.

These models are used to:
1. Parse and validate data from data/crews.json
2. Structure inventory data passed between tools
3. Ensure type safety across the application
"""

from pydantic import BaseModel, Field


class Consumable(BaseModel):
    """
    Represents a consumable inventory item.

    Attributes:
        name: Type of consumable (e.g., "valve_packings", "seals", "valves")
        quantity: Current quantity in inventory
        remaining_life_hours: Hours of remaining useful life
        surplus: Quantity available for borrowing to other crews
    """
    name: str
    quantity: int
    remaining_life_hours: int
    surplus: int = 0


class Crew(BaseModel):
    """
    Represents a frac crew with inventory.

    Attributes:
        crew_id: Unique identifier (e.g., "A", "B", "C")
        pumps: Number of pumps in this crew
        distance_miles: Distance from requesting crew (None for self)
        inventory: List of consumables in crew's inventory
    """
    crew_id: str
    pumps: int
    distance_miles: float | None = None
    inventory: list[Consumable]
