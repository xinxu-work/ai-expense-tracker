"""Read-only verification for the live Star Schema v3.1 database."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api"))

from dotenv import load_dotenv
from supabase import create_client


ACTIVE_END_DATE = "2030-01-01"
EXPECTED_TYPES = {"fixed", "variable", "income", "saving"}
EXPECTED_CATEGORIES = 22
EXPECTED_CATEGORY_BUDGETS = 6
EXPECTED_ENVELOPE_BUDGETS = 1
EXPECTED_MERCHANT_RULES = 19


def verify() -> int:
    load_dotenv(os.path.join(os.path.dirname(__file__), "api", ".env"))
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("FAILED: SUPABASE_URL and SUPABASE_KEY are required in api/.env")
        return 2

    supabase = create_client(url, key)
    errors: list[str] = []

    print("=" * 60)
    print("VERIFYING LIVE STAR SCHEMA v3.1 (READ ONLY)")
    print("=" * 60)

    types = supabase.table("types").select("id,name,sort_order").order("sort_order").execute()
    type_names = {row["name"] for row in types.data}
    print(f"\n[1] types: {len(types.data)} rows -> {', '.join(sorted(type_names))}")
    if type_names != EXPECTED_TYPES:
        errors.append(f"types: expected {sorted(EXPECTED_TYPES)}, got {sorted(type_names)}")

    categories = (
        supabase.table("categories")
        .select("id,name,type_id,types!inner(name)")
        .order("name")
        .execute()
    )
    by_type: dict[str, list[str]] = {}
    for category in categories.data:
        type_name = category["types"]["name"]
        by_type.setdefault(type_name, []).append(category["name"])

    print(f"\n[2] categories: {len(categories.data)} rows")
    for type_name in ["fixed", "variable", "income", "saving"]:
        print(f"  {type_name:<10} {len(by_type.get(type_name, []))} categories")
    if len(categories.data) != EXPECTED_CATEGORIES:
        errors.append(
            f"categories: expected {EXPECTED_CATEGORIES}, got {len(categories.data)}"
        )
    if any(not category.get("type_id") for category in categories.data):
        errors.append("categories: one or more type_id values are NULL")

    category_budgets = (
        supabase.table("budgets")
        .select("type_id,category_id,start_date,end_date,budget_amount,categories(name,type_id)")
        .not_.is_("category_id", "null")
        .eq("end_date", ACTIVE_END_DATE)
        .execute()
    )
    envelope_budgets = (
        supabase.table("budgets")
        .select("type_id,category_id,start_date,end_date,budget_amount")
        .is_("category_id", "null")
        .eq("end_date", ACTIVE_END_DATE)
        .execute()
    )
    print(
        f"\n[3] active budgets: {len(category_budgets.data)} category + "
        f"{len(envelope_budgets.data)} envelope"
    )
    if len(category_budgets.data) != EXPECTED_CATEGORY_BUDGETS:
        errors.append(
            "category budgets: expected "
            f"{EXPECTED_CATEGORY_BUDGETS}, got {len(category_budgets.data)}"
        )
    if len(envelope_budgets.data) != EXPECTED_ENVELOPE_BUDGETS:
        errors.append(
            "envelope budgets: expected "
            f"{EXPECTED_ENVELOPE_BUDGETS}, got {len(envelope_budgets.data)}"
        )
    for budget in category_budgets.data:
        category = budget.get("categories")
        if not category or category.get("type_id") != budget.get("type_id"):
            errors.append("budgets: a category budget is linked to the wrong type")
            break

    rules = (
        supabase.table("merchant_rules")
        .select("id,keyword,category_id,priority")
        .execute()
    )
    print(f"\n[4] merchant_rules: {len(rules.data)} rows")
    if len(rules.data) != EXPECTED_MERCHANT_RULES:
        errors.append(
            f"merchant_rules: expected {EXPECTED_MERCHANT_RULES}, got {len(rules.data)}"
        )

    pay_dates = supabase.table("pay_dates").select("pay_date,source").execute()
    periods = supabase.table("v_pay_periods").select("period_start,period_end").execute()
    print(f"\n[5] pay_dates: {len(pay_dates.data)}; pay periods: {len(periods.data)}")
    if len(periods.data) != len(pay_dates.data):
        errors.append("v_pay_periods: row count does not match pay_dates")
    if any(row.get("source") not in {"auto", "manual"} for row in pay_dates.data):
        errors.append("pay_dates: invalid source value")

    transactions = supabase.table("transactions").select("id,source").execute()
    print(f"\n[6] transactions preserved: {len(transactions.data)} rows")
    if not transactions.data:
        errors.append("transactions: expected existing rows after migration")
    if any(row.get("source") not in {"manual", "bank_import"} for row in transactions.data):
        errors.append("transactions: NULL or invalid source value")

    monthly_view = supabase.table("v_monthly_summary").select("*").limit(1).execute()
    budget_view = supabase.table("v_budget_vs_actual").select("*").limit(1).execute()
    print(
        "\n[7] public views reachable: "
        f"monthly={monthly_view.data is not None}, budget={budget_view.data is not None}"
    )

    print("\n" + "=" * 60)
    if errors:
        print(f"FAILED - {len(errors)} error(s):")
        for error in errors:
            print(f"  - {error}")
        print("=" * 60)
        return 1

    print("ALL CHECKS PASSED - Star Schema v3.1 is live")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(verify())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"FAILED: schema verification could not complete: {exc}")
        raise SystemExit(2) from exc
