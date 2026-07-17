"""Deterministic budget checks used by the API and AI agent.

The language model can decide when to call this service and explain its result,
but the affordability calculation itself stays in application code.
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


MONEY_PLACES = Decimal("0.01")


class CategoryNotFoundError(ValueError):
    """Raised when the requested expense category is not configured."""


def _money(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def _next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def month_bounds(value: date) -> tuple[date, date]:
    """Return an inclusive month start and exclusive month end."""
    start = value.replace(day=1)
    return start, _next_month(start)


def evaluate_purchase(
    *,
    item_name: str,
    price: Any,
    category_name: str,
    expense_type: str,
    period_start: date,
    period_end: date,
    budget_scope: str,
    budget_amount: Any | None,
    spent_so_far: Any,
    warning_threshold: float = 0.90,
) -> dict[str, Any]:
    """Evaluate a proposed purchase against a monthly budget.

    This answers whether the purchase fits the configured budget. It does not
    claim that the user has sufficient cash or provide financial advice.
    """
    purchase = _money(price)
    spent = _money(spent_so_far)
    common = {
        "item": item_name,
        "category": category_name,
        "expense_type": expense_type,
        "currency": "AUD",
        "period_start": period_start.isoformat(),
        "period_end_exclusive": period_end.isoformat(),
        "budget_scope": budget_scope,
        "purchase_price": float(purchase),
        "spent_so_far": float(spent),
    }

    if budget_amount is None:
        return {
            **common,
            "decision": "no_budget",
            "can_buy_within_budget": None,
            "budget_amount": None,
            "remaining_before_purchase": None,
            "projected_spend": float(spent + purchase),
            "remaining_after_purchase": None,
            "projected_utilisation_pct": None,
            "reason": (
                f"No monthly budget is configured for {category_name} or its "
                f"{expense_type} expense envelope."
            ),
        }

    budget = _money(budget_amount)
    projected = spent + purchase
    remaining_before = budget - spent
    remaining_after = budget - projected
    utilisation = (
        (projected / budget * Decimal("100")).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )
        if budget > 0
        else None
    )

    if projected > budget:
        decision = "over_budget"
        can_buy = False
        reason = (
            f"The purchase would exceed the {budget_scope} budget by "
            f"${abs(remaining_after):.2f}."
        )
    elif projected >= budget * Decimal(str(warning_threshold)):
        decision = "tight"
        can_buy = True
        reason = (
            f"The purchase fits, but would use {utilisation}% of the "
            f"{budget_scope} budget."
        )
    else:
        decision = "within_budget"
        can_buy = True
        reason = (
            f"The purchase fits the {budget_scope} budget with "
            f"${remaining_after:.2f} remaining."
        )

    return {
        **common,
        "decision": decision,
        "can_buy_within_budget": can_buy,
        "budget_amount": float(budget),
        "remaining_before_purchase": float(remaining_before),
        "projected_spend": float(projected),
        "remaining_after_purchase": float(remaining_after),
        "projected_utilisation_pct": float(utilisation) if utilisation is not None else None,
        "reason": reason,
    }


def assess_purchase(
    client: Any,
    *,
    item_name: str,
    price: float,
    category_name: str,
    purchase_date: date,
    warning_threshold: float = 0.90,
) -> dict[str, Any]:
    """Load the applicable budget and spending, then evaluate the purchase.

    A category budget takes precedence. If none exists, the service falls back
    to the category's type-level envelope budget (for example, the shared
    variable-expense budget used by Shopping, Groceries, and Dining Out).
    """
    category_result = (
        client.table("categories")
        .select("id,name,type_id,types(name)")
        .ilike("name", category_name)
        .limit(1)
        .execute()
    )
    if not category_result.data:
        raise CategoryNotFoundError(
            f"Category '{category_name}' was not found. Try 'Shopping' for shoes."
        )

    category = category_result.data[0]
    category_id = category["id"]
    type_id = category["type_id"]
    type_name = category["types"]["name"]
    purchase_day = purchase_date.isoformat()
    period_start, period_end = month_bounds(purchase_date)

    budget_fields = "id,type_id,category_id,start_date,end_date,budget_amount"
    category_budget = (
        client.table("budgets")
        .select(budget_fields)
        .eq("category_id", category_id)
        .lte("start_date", purchase_day)
        .gt("end_date", purchase_day)
        .order("start_date", desc=True)
        .limit(1)
        .execute()
    )

    if category_budget.data:
        budget = category_budget.data[0]
        budget_scope = "category"
    else:
        envelope_budget = (
            client.table("budgets")
            .select(budget_fields)
            .eq("type_id", type_id)
            .is_("category_id", "null")
            .lte("start_date", purchase_day)
            .gt("end_date", purchase_day)
            .order("start_date", desc=True)
            .limit(1)
            .execute()
        )
        budget = envelope_budget.data[0] if envelope_budget.data else None
        budget_scope = f"{type_name}_envelope" if budget else "unbudgeted_category"

    transactions = (
        client.table("transactions")
        .select("amount,categories!inner(type_id)")
        .gte("transaction_date", period_start.isoformat())
        .lt("transaction_date", period_end.isoformat())
    )
    if budget_scope == "category":
        transactions = transactions.eq("category_id", category_id)
    else:
        transactions = transactions.eq("categories.type_id", type_id)

    transaction_result = transactions.execute()
    spent_so_far = sum(_money(row["amount"]) for row in transaction_result.data)

    return evaluate_purchase(
        item_name=item_name,
        price=price,
        category_name=category["name"],
        expense_type=type_name,
        period_start=period_start,
        period_end=period_end,
        budget_scope=budget_scope,
        budget_amount=budget["budget_amount"] if budget else None,
        spent_so_far=spent_so_far,
        warning_threshold=warning_threshold,
    )
