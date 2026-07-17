"""
CommBank CSV Import → Supabase Expense Tracker
================================================
Pipeline:
  1. Parse CommBank CSV (Date, Amount, Description, Balance)
  2. Auto-categorize via merchant_rules keyword matching
  3. Flag unknowns for manual review
  4. Dedup (skip already-imported rows)
  5. Upsert into transactions table

CommBank CSV format (typical):
  Date,Amount,Description,Balance
  12/06/2026,-88.70,Woolworths Group Ltd Sydney AU,12450.30
  12/06/2026,5500.00,SALARY PAYMENT,17950.30

Usage:
  python import_commbank.py path/to/statement.csv [--dry-run] [--detect-pay-dates]
"""

import csv, sys, os
from datetime import datetime, date
from uuid import UUID
from typing import Optional

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv(os.path.join(os.path.dirname(__file__), "api", ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Set SUPABASE_URL and SUPABASE_KEY in api/.env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SALARY_CATEGORY = "Salary"
SALARY_MIN_AMOUNT = 3000  # minimum amount to auto-detect as salary
RENT_CATEGORIES = {"Rent"}  # categories considered as rent transfers
TRANSFER_KEYWORDS = ["TRANSFER", "INTERNET TRANSFER", "DIRECT CREDIT", "PAYMENT"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_merchant_rules() -> list[dict]:
    """Load all merchant_rules from Supabase, sorted by priority desc."""
    result = supabase.table("merchant_rules") \
        .select("keyword, category_id") \
        .order("priority", desc=True) \
        .execute()
    return result.data


def categorise_by_rules(raw_desc: str, rules: list[dict]) -> Optional[str]:
    """Match raw_description against merchant_rules.keyword (case-insensitive)."""
    upper_desc = raw_desc.upper()
    for rule in rules:
        if rule["keyword"].upper() in upper_desc:
            return rule["category_id"]
    return None


def parse_commbank_csv(filepath: str) -> list[dict]:
    """Parse CommBank CSV into list of row dicts with standardised fields."""
    rows = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for line_num, row in enumerate(reader, start=2):
            try:
                # CommBank uses DD/MM/YYYY
                txn_date = datetime.strptime(row["Date"].strip(), "%d/%m/%Y").date()
                amount = float(row["Amount"].strip().replace(",", ""))
                description = row["Description"].strip()
                balance_str = row.get("Balance", "").strip().replace(",", "")
                balance = float(balance_str) if balance_str else None

                # Positive amount = credit (income), negative = debit (expense)
                # Convert to absolute for our schema (category type distinguishes)
                rows.append({
                    "transaction_date": txn_date.isoformat(),
                    "amount": abs(amount),
                    "raw_description": description,
                    "is_credit": amount > 0,
                    "balance": balance,
                    "source_line": line_num,
                })
            except (ValueError, KeyError) as e:
                print(f"  [skip] Line {line_num}: parse error — {e}")
    return rows


def insert_transaction(txn: dict, batch_id: str, dry_run: bool = False) -> bool:
    """Insert a single transaction into Supabase. Skip duplicates."""
    if dry_run:
        status = "✓" if txn.get("category_id") else "?"
        print(f"  [{status}] {txn['transaction_date']} | ${txn['amount']:,.2f} | "
              f"{txn['raw_description'][:50]} | cat={txn.get('category_name', 'UNKNOWN')}")
        return False

    try:
        # Dedup check: same date + amount + raw_description
        existing = supabase.table("transactions") \
            .select("id") \
            .eq("transaction_date", txn["transaction_date"]) \
            .eq("amount", txn["amount"]) \
            .eq("raw_description", txn["raw_description"]) \
            .execute()

        if existing.data:
            return False  # already imported

        data = {
            "transaction_date": txn["transaction_date"],
            "amount": txn["amount"],
            "raw_description": txn["raw_description"],
            "description": txn.get("description", txn["raw_description"])[:255],
            "category_id": txn.get("category_id"),
            "source": "bank_import",
            "import_batch_id": batch_id,
            "payment_method": "transfer" if txn.get("is_credit") else "card",
        }
        # Remove None category_id — will need manual review
        if data["category_id"] is None:
            del data["category_id"]

        supabase.table("transactions").insert(data).execute()
        return True
    except Exception as e:
        print(f"  [ERROR] {txn['raw_description'][:50]}: {e}")
        return False


def detect_pay_dates():
    """Scan existing transactions for salary deposits, populate pay_dates."""
    salary_cat = supabase.table("categories") \
        .select("id").eq("name", SALARY_CATEGORY).single().execute()
    salary_id = salary_cat.data["id"]

    result = supabase.table("transactions") \
        .select("transaction_date") \
        .eq("category_id", salary_id) \
        .gte("amount", SALARY_MIN_AMOUNT) \
        .order("transaction_date") \
        .execute()

    inserted = 0
    for row in result.data:
        dt = row["transaction_date"]
        # Check if already in pay_dates
        existing = supabase.table("pay_dates") \
            .select("pay_date").eq("pay_date", dt).execute()
        if not existing.data:
            supabase.table("pay_dates").insert({
                "pay_date": dt,
                "source": "auto",
                "note": f"Detected from Salary transactions"
            }).execute()
            inserted += 1
            print(f"  + Pay date: {dt}")

    if inserted == 0:
        print("  No new pay dates found.")
    return inserted


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python import_commbank.py <csv_file> [--dry-run] [--detect-pay-dates]")
        print("  --dry-run          Preview only, no insert")
        print("  --detect-pay-dates  Auto-detect salary deposits as pay dates after import")
        sys.exit(1)

    csv_path = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    detect = "--detect-pay-dates" in sys.argv

    if dry_run:
        print("=" * 60)
        print(" DRY RUN — preview only (no changes)")
        print("=" * 60)

    # 1. Parse CSV
    print(f"\n[1] Parsing: {csv_path}")
    rows = parse_commbank_csv(csv_path)
    print(f"    {len(rows)} transactions found")
    if not rows:
        print("    No valid rows — check CSV format.")
        return

    # 2. Load merchant rules
    print("\n[2] Loading merchant rules...")
    rules = load_merchant_rules()
    print(f"    {len(rules)} rules loaded")

    # 3. Load category lookup
    cats_result = supabase.table("categories").select("id, name").execute()
    cat_map = {c["id"]: c["name"] for c in cats_result.data}
    print(f"    {len(cat_map)} categories available")

    # 4. Categorise and prepare transactions
    batch_id = f"{date.today().strftime('%Y%m%d')}_commbank"
    categorised = 0
    unknown = 0

    for row in rows:
        cat_id = categorise_by_rules(row["raw_description"], rules)
        if cat_id:
            row["category_id"] = cat_id
            row["category_name"] = cat_map.get(cat_id, "?")
            categorised += 1
        else:
            row["category_id"] = None
            row["category_name"] = None
            unknown += 1

    print(f"\n[3] Categorisation: {categorised} matched, {unknown} unknown")

    # 5. Insert (or dry-run preview)
    print(f"\n[4] {'DRY RUN preview' if dry_run else 'Importing'} (batch: {batch_id}):")
    inserted = 0
    skipped = 0
    for row in rows:
        ok = insert_transaction(row, batch_id, dry_run)
        if ok:
            inserted += 1
        else:
            skipped += 1

    if not dry_run:
        print(f"\n    Imported: {inserted} new, {skipped} skipped (duplicates)")
    else:
        print(f"\n    Preview: {inserted + skipped} would be processed")

    # 6. Auto-detect pay dates
    if detect and not dry_run:
        print(f"\n[5] Detecting pay dates (Salary >= ${SALARY_MIN_AMOUNT:,})...")
        detect_pay_dates()

    print("\nDone.")

    if unknown > 0:
        print(f"\n⚠ {unknown} transactions could not be categorised.")
        print("  Add merchant_rules or assign categories manually.")
        if dry_run:
            print("  Look for [?] rows above.")


if __name__ == "__main__":
    main()
