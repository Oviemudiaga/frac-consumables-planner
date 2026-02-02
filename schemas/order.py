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

    # TODO: Implement fields
    pass


class OrderLineItem(BaseModel):
    """A single line item in the order plan."""

    # TODO: Implement fields
    pass


class OrderPlan(BaseModel):
    """Complete order plan."""

    # TODO: Implement fields
    pass
