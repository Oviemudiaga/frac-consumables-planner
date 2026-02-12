"""
Pydantic schemas for structured chatbot responses.

This module defines the response structure for the chatbot to ensure
it returns recommendations that match the deterministic order plan.
"""

from pydantic import BaseModel, Field


class OrderRecommendation(BaseModel):
    """A single order/borrow recommendation from the order plan."""

    consumable: str = Field(
        description="Consumable name: valve_packings, seals, or plungers"
    )
    action: str = Field(
        description="Action type: 'borrow', 'order', or 'none_needed'"
    )
    quantity: int = Field(
        ge=0,
        description="Quantity to borrow or order (0 if none needed)"
    )
    source: str | None = Field(
        default=None,
        description="Crew ID to borrow from (e.g., 'B'), only if action is 'borrow'"
    )


class ChatbotResponse(BaseModel):
    """Structured chatbot response with order plan recommendations."""

    answer: str = Field(
        description="Natural language answer to the user's question"
    )
    recommendations: list[OrderRecommendation] = Field(
        default_factory=list,
        description="Order/borrow recommendations extracted from the order plan data"
    )
