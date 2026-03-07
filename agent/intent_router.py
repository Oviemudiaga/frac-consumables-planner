"""
Intent router for the chatbot using a Router Agent pattern.

Uses an LLM with structured output to classify user messages into intents.
This replaces keyword matching with nuanced understanding of user questions.

The router is a specialized function:
    (message, context_mode) -> ChatIntent

Intents:
- "status": Questions about pump health, remaining life, conditions
- "order": Questions about what to order, borrow, or plan
- "cost": Questions about costs, pricing, financials
- "explain": Explanation of decisions OR what-if/sensitivity analysis

Usage:
    from ui.intent_router import classify_intent, ChatIntent

    intent = classify_intent("what should I order?", model="llama3")
"""

from enum import Enum
from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama


class ChatIntent(str, Enum):
    """Possible chat intents."""
    STATUS = "status"
    ORDER = "order"
    COST = "cost"
    EXPLAIN = "explain"


class IntentClassification(BaseModel):
    """Structured output schema for intent classification."""
    intent: ChatIntent = Field(
        description="The classified intent of the user message"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence level of the classification (0.0 to 1.0)"
    )


INTENT_ROUTER_PROMPT = """You are an intent classification agent for a frac consumables planner application.
Your ONLY job is to classify the user's message into exactly one intent.

## INTENTS

- "status": Questions about pump health, remaining life, equipment conditions, fleet overview, which pumps are critical/marginal/healthy.
- "order": Questions about what to order or borrow, consumable needs, shortfalls, order plans, transfer logistics, recommendations for what Crew A should do.
- "cost": Questions about costs, pricing, cost comparison between borrowing and ordering, shipping costs, travel costs, savings, budget, financial analysis.
- "explain": Requests to explain WHY a decision was made, what-if/sensitivity analysis (e.g. "what if weather changes", "what if distance doubles"), scenario comparisons, or deeper analysis of the plan.

## RULES

1. If the user asks "what if..." or "suppose..." or "what would happen if..." -> ALWAYS "explain"
2. If the user asks "why..." about a decision -> "explain"
3. If the user asks "how much does it cost" or mentions dollars/pricing -> "cost"
4. If the user asks "what should I order/borrow" or about quantities/shortfalls -> "order"
5. If the user asks about pump health, remaining life, or equipment status -> "status"
6. When ambiguous, prefer: explain > cost > order > status

## CONTEXT

The user is on the "{context_mode}" tab:
- "pump_status": They are viewing pump health dashboards
- "job_planning": They are planning orders and analyzing costs

Classify this message now."""


def classify_intent(
    message: str,
    model: str = "llama3",
    context_mode: str = "pump_status",
) -> ChatIntent:
    """
    Classify a user message into a chat intent using an LLM router.

    Args:
        message: The user's chat message
        model: Ollama model name for classification
        context_mode: Current UI tab ("pump_status" or "job_planning")

    Returns:
        ChatIntent enum value
    """
    try:
        llm = ChatOllama(model=model, temperature=0)
        structured_llm = llm.with_structured_output(IntentClassification)

        prompt = INTENT_ROUTER_PROMPT.format(context_mode=context_mode)

        result = structured_llm.invoke([
            {"role": "system", "content": prompt},
            {"role": "user", "content": message},
        ])

        return result.intent

    except Exception:
        # Fallback to keyword matching if LLM fails
        return _keyword_fallback(message)


def _keyword_fallback(message: str) -> ChatIntent:
    """
    Fallback keyword-based classification if the LLM is unavailable.

    Args:
        message: The user's chat message

    Returns:
        ChatIntent enum value
    """
    lower = message.lower()

    explain_keywords = [
        "explain", "why", "what if", "suppose", "assuming",
        "sensitivity", "scenario", "what would happen",
        "how does", "analyze", "breakdown",
    ]
    cost_keywords = [
        "cost", "price", "dollar", "$", "budget", "savings",
        "how much", "expensive", "cheap", "financial",
    ]
    order_keywords = [
        "order", "borrow", "what to order", "shortfall",
        "recommendation", "consumable", "transfer", "pickup",
    ]
    status_keywords = [
        "status", "health", "remaining life", "critical",
        "marginal", "pump", "condition",
    ]

    for kw in explain_keywords:
        if kw in lower:
            return ChatIntent.EXPLAIN
    for kw in cost_keywords:
        if kw in lower:
            return ChatIntent.COST
    for kw in order_keywords:
        if kw in lower:
            return ChatIntent.ORDER
    for kw in status_keywords:
        if kw in lower:
            return ChatIntent.STATUS

    return ChatIntent.STATUS
