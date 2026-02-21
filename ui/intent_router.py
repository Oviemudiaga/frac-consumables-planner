"""
Intent router for the chatbot.

Classifies user messages into one of three intents:
- "status": Questions about pump health, remaining life, conditions
- "order": Questions about what to order, borrow, or plan
- "cost": Questions about costs, pricing, financials

Uses keyword matching for deterministic, reliable classification.

Usage:
    from ui.intent_router import classify_intent, ChatIntent

    intent = classify_intent("what should I order?")
    # ChatIntent.ORDER
"""

from enum import Enum


class ChatIntent(str, Enum):
    """Possible chat intents."""
    STATUS = "status"
    ORDER = "order"
    COST = "cost"


# Priority: cost > order > status
# Cost is checked first because cost questions often contain order words
# (e.g., "how much does the order cost?" should route to COST, not ORDER)

COST_KEYWORDS: list[str] = [
    "cost", "price", "pricing", "expensive", "cheap", "cheaper",
    "budget", "spend", "spending", "dollar", "dollars", "$",
    "financial", "financials", "money", "savings", "save",
    "cost comparison", "cost analysis",
    "borrow vs order", "order vs borrow",
    "how much", "total cost", "shipping cost", "travel cost",
    "labor cost",
]

ORDER_KEYWORDS: list[str] = [
    "order", "ordering", "borrow", "borrowing",
    "what to order", "what to borrow", "what do i need",
    "what does crew a need", "what should i order",
    "what should we order", "recommendation", "recommend",
    "supply", "supplies", "consumable", "consumables",
    "shortfall", "shortage", "replenish",
    "order plan", "order summary", "generate order",
    "transfer", "pickup", "route",
]

STATUS_KEYWORDS: list[str] = [
    "status", "health", "healthy", "condition", "conditions",
    "remaining life", "life remaining", "how long",
    "critical", "marginal", "failing", "fail",
    "pump status", "fleet status", "pump health",
    "which pump", "worst pump", "best pump",
    "crew status",
]


def classify_intent(message: str) -> ChatIntent:
    """
    Classify a user message into a chat intent.

    Priority: cost > order > status (explicit) > status (default).

    Args:
        message: The user's chat message

    Returns:
        ChatIntent enum value
    """
    lower = message.lower()

    for keyword in COST_KEYWORDS:
        if keyword in lower:
            return ChatIntent.COST

    for keyword in ORDER_KEYWORDS:
        if keyword in lower:
            return ChatIntent.ORDER

    for keyword in STATUS_KEYWORDS:
        if keyword in lower:
            return ChatIntent.STATUS

    # Default: status (safe — LLM only talks about pump data)
    return ChatIntent.STATUS
