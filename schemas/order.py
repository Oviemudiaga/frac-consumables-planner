"""
Pydantic models for order planning output.

Defines:
- BorrowSource: Where consumables are borrowed from (crew ID + quantity)
- OrderLineItem: Single consumable's order breakdown (need, borrow, order qty)
- OrderPlan: Complete order plan with all line items and recommendation

These models structure the agent's output and are used to:
1. Return structured data from the order_planner tool
2. Render the editable order form in Streamlit
3. Ensure consistent order data throughout the application
"""

from pydantic import BaseModel, Field


class BorrowSource(BaseModel):
    """
    Represents a borrowing source for consumables.

    Attributes:
        crew_id: ID of crew to borrow from
        quantity: Quantity to borrow
    """
    crew_id: str
    quantity: int


class OrderLineItem(BaseModel):
    """
    Order details for a single consumable type.

    Attributes:
        consumable_name: Name of the consumable
        total_needed: Total quantity needed for the job
        on_hand_usable: Quantity on hand with sufficient remaining life
        borrow: List of crews to borrow from
        borrow_total: Total quantity borrowed
        to_order: Quantity that must be ordered (need - on_hand - borrow)
        unit_cost: Cost per unit (mock value)
    """
    consumable_name: str
    total_needed: int
    on_hand_usable: int
    borrow: list[BorrowSource]
    borrow_total: int
    to_order: int
    unit_cost: float = 100.0


class OrderPlan(BaseModel):
    """
    Complete order plan for a job.

    Attributes:
        crew_id: Requesting crew's ID
        job_duration_hours: Job duration in hours
        pump_count: Number of pumps for the job
        items: Order line items for each consumable type
        total_order_cost: Total cost of items to order
        recommendation: Natural language explanation from agent
    """
    crew_id: str
    job_duration_hours: int
    pump_count: int
    items: list[OrderLineItem]
    total_order_cost: float
    recommendation: str
