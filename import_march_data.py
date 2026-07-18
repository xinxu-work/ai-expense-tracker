"""
Import March 2026 living expenses from Excel → Supabase.

Usage:  python import_march_data.py           # imports March data
        python import_march_data.py --dry-run  # preview only, no insert
"""
import os, sys, argparse
from datetime import date

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

# === Config ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_PATH = r"c:\Users\XinXu\iCloudDrive\Xin_Xin_File\DS\Import\Living_Expense_Mar.xlsx"

load_dotenv(os.path.join(BASE_DIR, "api", ".env"))
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# === Mapping: Excel column → (category_name, date_in_period, description_template) ===
# Period: 3.15 - 4.12, 2026. We assign dates within this range.
MAPPING = [
    # --- INCOME ---
    {"col": "工资", "category": "Salary", "date": "2026-03-16", "desc": "Monthly salary"},
    # --- Fixed bills (assigned mid-March) ---
    {"col": "房租", "category": "Rent", "date": "2026-03-18", "desc": "Monthly rent"},
    {"col": "Gym", "category": "Health", "date": "2026-03-16", "desc": "Gym membership"},
    {"col": "Health insurance", "category": "Insurance", "date": "2026-03-20", "desc": "Health insurance"},
    {"col": "Mobile plan", "category": "Phone & Internet", "date": "2026-03-20", "desc": "Mobile plan"},
    {"col": "Net Bill", "category": "Phone & Internet", "date": "2026-03-22", "desc": "Internet bill"},
    {"col": "Apple bill", "category": "Subscriptions", "date": "2026-03-22", "desc": "Apple subscription"},
    {"col": "Google bill", "category": "Subscriptions", "date": "2026-03-22", "desc": "Google subscription"},
    {"col": "Netmusic bill", "category": "Subscriptions", "date": "2026-03-22", "desc": "NetEase Music subscription"},
    {"col": "Notion", "category": "Subscriptions", "date": "2026-03-22", "desc": "Notion subscription"},
    {"col": "CLAUDE", "category": "Subscriptions", "date": "2026-03-22", "desc": "Claude AI subscription"},
    {"col": "Linkt", "category": "Transport", "date": "2026-03-25", "desc": "Linkt toll"},
    # --- Transport (late March) ---
    {"col": "Transport", "category": "Transport", "date": "2026-03-25", "desc": "Public transport"},
    {"col": "Fuel", "category": "Transport", "date": "2026-03-28", "desc": "Fuel"},
    {"col": "Uber", "category": "Transport", "date": "2026-03-27", "desc": "Uber ride"},
    # --- Entertainment / Shopping (late March / early April) ---
    {"col": "Ticket", "category": "Entertainment", "date": "2026-04-02", "desc": "Event ticket"},
    {"col": "Other", "category": "Other Expense", "date": "2026-04-01", "desc": "Miscellaneous expense"},
]

# === CBA breakdown (花销 CBA = $565.80) ===
# This account mixes categories — example breakdown per user request
CBA_BREAKDOWN = [
    {"category": "Groceries", "amount": 300.00, "date": "2026-03-20", "desc": "Groceries (CBA) — Aldi/WWS/etc"},
    {"category": "Dining Out", "amount": 150.00, "date": "2026-03-24", "desc": "Dining out (CBA)"},
    {"category": "Other Expense", "amount": 100.00, "date": "2026-04-02", "desc": "Transfer to friend — shared bill (CBA)"},
    {"category": "Other Expense", "amount": 15.80, "date": "2026-04-05", "desc": "Other spending (CBA)"},
]

# === ING breakdown (花销 ING = $100) ===
# Confirmed by user — use this example breakdown
ING_BREAKDOWN = [
    {"category": "Entertainment", "amount": 60.00, "date": "2026-03-27", "desc": "Entertainment (ING)"},
    {"category": "Shopping", "amount": 40.00, "date": "2026-04-03", "desc": "Shopping (ING)"},
]

# === ING Joint breakdown (花销 ING Joint = $450) ===
# Joint account — shared living expenses. Confirmed example breakdown.
ING_JOINT_BREAKDOWN = [
    {"category": "Groceries", "amount": 200.00, "date": "2026-03-21", "desc": "Groceries — joint (ING Joint)"},
    {"category": "Utilities", "amount": 150.00, "date": "2026-03-23", "desc": "Utilities — joint (ING Joint)"},
    {"category": "Dining Out", "amount": 100.00, "date": "2026-04-01", "desc": "Dining out — joint (ING Joint)"},
]


def connect_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL/KEY not set in api/.env")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_category_map(supabase):
    """Fetch categories → {name: uuid} mapping."""
    result = supabase.table("categories").select("id, name").execute()
    return {row["name"]: row["id"] for row in result.data}


def read_excel():
    df = pd.read_excel(EXCEL_PATH, header=None)
    headers = df.iloc[0].tolist()
    values = df.iloc[1].tolist()  # Row 1 = March
    march_row = {headers[i]: values[i] for i in range(len(headers))}
    return headers, march_row


def build_transactions(march_row, category_map, dry_run=False):
    """Convert Excel row + breakdowns → list of transaction dicts."""
    transactions = []
    warnings = []

    # Process direct column mappings
    for m in MAPPING:
        val = march_row.get(m["col"])
        if pd.isna(val) or val == 0:
            continue
        cat_id = category_map.get(m["category"])
        if not cat_id:
            warnings.append(f"Category '{m['category']}' not found in DB — skipping {m['col']}")
            continue
        transactions.append({
            "transaction_date": m["date"],
            "category_id": str(cat_id),
            "amount": float(val),
            "description": m["desc"],
            "payment_method": "card",
        })

    # Process bank-account breakdowns
    breakdowns = [
        ("CBA", CBA_BREAKDOWN, march_row.get("花销 CBA ", 0)),
        ("ING", ING_BREAKDOWN, march_row.get("花销 ING", 0)),
        ("ING Joint", ING_JOINT_BREAKDOWN, march_row.get("花销 ING Joint", 0)),
    ]

    for label, breakdown, expected_total in breakdowns:
        if pd.isna(expected_total) or expected_total == 0:
            continue
        actual_total = sum(b["amount"] for b in breakdown)
        diff = round(float(expected_total) - actual_total, 2)
        if abs(diff) > 0.01:
            warnings.append(
                f"[WARN] {label} breakdown totals ${actual_total:.2f}, "
                f"but Excel has ${float(expected_total):.2f} (diff: ${diff:.2f}). "
                "Adjust breakdown amounts."
            )

        for b in breakdown:
            cat_id = category_map.get(b["category"])
            if not cat_id:
                warnings.append(f"Category '{b['category']}' not found — skipping {label} item")
                continue
            transactions.append({
                "transaction_date": b["date"],
                "category_id": str(cat_id),
                "amount": b["amount"],
                "description": b["desc"],
                "payment_method": "card",
            })

    return transactions, warnings


def insert_transactions(supabase, transactions):
    """Bulk insert transactions into Supabase. Returns list of inserted IDs."""
    inserted = []
    errors = []
    for i, txn in enumerate(transactions):
        try:
            result = supabase.table("transactions").insert(txn).execute()
            inserted.append(result.data[0]["id"])
            print(f"  [{i+1}/{len(transactions)}] {txn['transaction_date']} | "
                  f"${txn['amount']:>8.2f} | {txn['description'][:50]}")
        except Exception as e:
            errors.append(f"Row {i+1} failed: {e}")
            print(f"  [{i+1}/{len(transactions)}] ERROR: {e}")
    return inserted, errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no insert")
    args = parser.parse_args()

    print("=" * 60)
    print("Expense Tracker — March 2026 Data Import")
    print("=" * 60)

    # 1. Read Excel
    headers, march_row = read_excel()
    print(f"\n[1] Excel loaded: {len(headers)} columns, period: {march_row['Month']}")

    # 2. Connect
    print("\n[2] Connecting to Supabase...")
    try:
        supabase = connect_supabase()
    except Exception as e:
        print(f"  Connection failed: {e}")
        print("  Check your network/VPN and try again.")
        sys.exit(1)

    # 3. Get categories
    print("\n[3] Fetching categories...")
    category_map = get_category_map(supabase)
    print(f"  {len(category_map)} categories loaded")
    for name, uid in sorted(category_map.items()):
        print(f"    {name}: {uid}")

    # 4. Build transactions
    print(f"\n[4] Building transactions...")
    transactions, warnings = build_transactions(march_row, category_map, dry_run=args.dry_run)

    for w in warnings:
        print(f"  {w}")

    print(f"\n  Total transactions to insert: {len(transactions)}")
    total_amount = sum(t["amount"] for t in transactions)
    print(f"  Total amount: ${total_amount:,.2f}")

    if args.dry_run:
        print("\n  [DRY RUN — no data inserted]")
        print("\n  Preview:")
        for t in transactions:
            cat_name = [k for k, v in category_map.items() if str(v) == t["category_id"]][0]
            print(f"    {t['transaction_date']} | ${t['amount']:>8.2f} | {cat_name:<20s} | {t['description']}")
        return

    # 5. Confirm
    print(f"\n[5] Ready to insert {len(transactions)} transactions.")
    ans = input("  Proceed? [y/N]: ").strip().lower()
    if ans != "y":
        print("  Aborted.")
        return

    # 6. Insert
    print(f"\n[6] Inserting...")
    inserted, errors = insert_transactions(supabase, transactions)

    print(f"\n{'=' * 60}")
    print(f"  Inserted: {len(inserted)}")
    print(f"  Errors:   {len(errors)}")
    print(f"{'=' * 60}")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  {e}")


if __name__ == "__main__":
    main()
