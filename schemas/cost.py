"""
Pydantic schemas for cost analysis used by the Cost Analyzer Agent.

This module defines cost breakdowns and configuration for comparing
borrow vs order costs.

Usage:
    from schemas.cost import CostConfig, CostBreakdown, ConsumablePricing
"""

from pydantic import BaseModel, Field


class ConsumablePricing(BaseModel):
    """Pricing information for a single consumable type."""

    unit_price: float = Field(
        ge=0.0,
        description="Price per unit in dollars"
    )
    supplier_lead_time_days: int = Field(
        ge=0,
        description="Lead time for supplier delivery in days"
    )


class TravelCostConfig(BaseModel):
    """Configuration for travel-related costs."""

    cost_per_mile: float = Field(
        default=2.50,
        ge=0.0,
        description="Cost per mile traveled in dollars"
    )
    cost_per_hour_labor: float = Field(
        default=75.00,
        ge=0.0,
        description="Labor cost per hour in dollars"
    )
    average_speed_mph: float = Field(
        default=30.0,
        gt=0.0,
        description="Average travel speed in miles per hour"
    )


class ShippingCostConfig(BaseModel):
    """Configuration for shipping costs when ordering."""

    base_cost: float = Field(
        default=50.00,
        ge=0.0,
        description="Base shipping cost in dollars"
    )
    per_unit_cost: float = Field(
        default=5.00,
        ge=0.0,
        description="Additional cost per unit shipped in dollars"
    )
    expedited_multiplier: float = Field(
        default=2.0,
        ge=1.0,
        description="Multiplier for expedited shipping"
    )


class CostConfig(BaseModel):
    """Complete configuration for cost calculations."""

    travel: TravelCostConfig = Field(
        default_factory=TravelCostConfig,
        description="Travel cost configuration"
    )
    consumables: dict[str, ConsumablePricing] = Field(
        default_factory=lambda: {
            "valve_packings": ConsumablePricing(unit_price=150.00, supplier_lead_time_days=2),
            "seals": ConsumablePricing(unit_price=85.00, supplier_lead_time_days=1),
            "plungers": ConsumablePricing(unit_price=250.00, supplier_lead_time_days=3),
        },
        description="Pricing for each consumable type"
    )
    shipping: ShippingCostConfig = Field(
        default_factory=ShippingCostConfig,
        description="Shipping cost configuration"
    )


class ItemCostBreakdown(BaseModel):
    """Cost breakdown for a single consumable item."""

    consumable: str = Field(description="Consumable name")
    quantity: int = Field(ge=0, description="Quantity needed")
    borrow_cost: float = Field(ge=0.0, description="Cost to borrow (travel costs)")
    order_cost: float = Field(ge=0.0, description="Cost to order (parts + shipping)")
    recommended_action: str = Field(description="'borrow', 'order', or 'none_needed'")


class CostBreakdown(BaseModel):
    """Complete cost breakdown comparing borrow vs order options."""

    items: list[ItemCostBreakdown] = Field(
        default_factory=list,
        description="Cost breakdown per consumable item"
    )
    travel_cost: float = Field(
        ge=0.0,
        description="Total travel cost (distance × $/mile + time × $/hour)"
    )
    total_borrow_cost: float = Field(
        ge=0.0,
        description="Total cost if borrowing all items"
    )
    total_order_cost: float = Field(
        ge=0.0,
        description="Total cost if ordering all items"
    )
    total_cost: float = Field(
        ge=0.0,
        description="Total cost for recommended actions"
    )
    savings: float = Field(
        default=0.0,
        description="Money saved by following recommendation vs ordering"
    )
    recommendation: str = Field(
        description="Overall recommendation: 'borrow', 'order', or 'mixed'"
    )
    recommendation_summary: str = Field(
        default="",
        description="Human-readable summary of the recommendation"
    )
