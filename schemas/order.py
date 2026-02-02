"""
Pydantic models for order plan output.

This module defines the output models for the order planning system:
- BorrowSource: A source crew for borrowing consumables
- OrderLineItem: A single line item in the order plan
- OrderPlan: Complete order plan with all line items

Usage:
    from schemas.order import OrderPlan, OrderLineItem, BorrowSource

    borrow = BorrowSource(crew_id="B", quantity=5, distance=3.5)
    item = OrderLineItem(consumable_name="seals", ...)
    plan = OrderPlan(crew_id="A", items=[item], ...)
"""

from pydantic import BaseModel, Field


class BorrowSource(BaseModel):
    """A source crew for borrowing."""

    crew_id: str = Field(description="ID of the crew to borrow from")
    quantity: int = Field(gt=0, description="Number of consumables to borrow")
    distance: float = Field(ge=0, description="Distance to the crew in miles")


class OrderLineItem(BaseModel):
    """A single line item in the order plan."""

    consumable_name: str = Field(description="Name of the consumable (valve_packings, seals, or plungers)")
    pumps_needing: int = Field(ge=0, description="Number of pumps needing this consumable")
    total_needed: int = Field(ge=0, description="Total quantity needed")
    on_hand: int = Field(ge=0, description="Quantity available in Crew A's spares")
    borrow_sources: list[BorrowSource] = Field(default_factory=list, description="Crews to borrow from")
    to_order: int = Field(ge=0, description="Quantity to order from supplier")


class OrderPlan(BaseModel):
    """Complete order plan."""

    crew_id: str = Field(description="ID of the crew this plan is for")
    job_duration_hours: int = Field(gt=0, description="Job duration in hours")
    items: list[OrderLineItem] = Field(description="Order line items for each consumable")
