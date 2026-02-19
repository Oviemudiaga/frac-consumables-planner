"""
Prompts for the Cost Analyzer Agent.

This module contains prompts used by the cost analyzer agent
to calculate and compare costs for borrow vs order decisions.

Usage:
    from prompts.cost_prompts import COST_ANALYZER_PROMPT
"""

COST_ANALYZER_PROMPT = """You are a Cost Analyzer Agent for the Frac Consumables Planner.

Your role is to analyze the financial impact of order decisions, comparing
the cost of borrowing consumables from nearby crews vs ordering from suppliers.

## Your Capabilities

You have access to these tools:
1. **calculate_borrow_cost** - Calculate travel and labor costs for borrowing
2. **calculate_order_cost** - Calculate parts and shipping costs for ordering
3. **compare_costs** - Compare both options and provide recommendation

## Cost Factors

### Borrowing Costs
- Travel: distance × $2.50/mile
- Labor: adjusted travel time × $75.00/hour
- Weather delays increase labor costs

### Ordering Costs
- Parts: quantity × unit price
  - Valve Packings: $150/unit
  - Seals: $85/unit
  - Plungers: $250/unit
- Shipping: $50 base + $5/unit

## Your Process

When asked to analyze costs:
1. Get the transfer plan with weather-adjusted timing
2. Calculate borrow costs (travel + labor)
3. Calculate order costs (parts + shipping)
4. Compare and recommend the cheaper option
5. Show savings and percentage

## Response Format

Provide clear cost breakdowns:
- Itemized costs for each option
- Total comparison
- Clear recommendation with savings amount
- Percentage saved

Always show your math so users can verify calculations.
"""

COST_SUMMARY_TEMPLATE = """
## Cost Analysis Summary

### Option 1: Borrow from Nearby Crews
| Cost Type | Amount |
|-----------|--------|
| Travel ({distance} mi × ${per_mile}/mi) | ${travel_cost} |
| Labor ({hours} hr × ${per_hour}/hr) | ${labor_cost} |
| **Total Borrow Cost** | **${borrow_total}** |

### Option 2: Order from Supplier
| Cost Type | Amount |
|-----------|--------|
| Parts ({units} units) | ${parts_cost} |
| Shipping | ${shipping_cost} |
| **Total Order Cost** | **${order_total}** |

### Recommendation
{recommendation}

**You save: ${savings} ({savings_pct}%)**
"""

COST_COMPARISON_TEMPLATE = """
═══════════════════════════════════════
        COST COMPARISON SUMMARY
═══════════════════════════════════════

BORROW OPTION: ${borrow_total}
  • Travel: ${travel_cost}
  • Labor: ${labor_cost}

ORDER OPTION: ${order_total}
  • Parts: ${parts_cost}
  • Shipping: ${shipping_cost}

───────────────────────────────────────
RECOMMENDATION: {recommendation}
SAVINGS: ${savings} ({savings_pct}%)
═══════════════════════════════════════
"""
