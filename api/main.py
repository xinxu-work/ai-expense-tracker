"""
Expense Tracker API
FastAPI backend connecting to Supabase PostgreSQL — Star Schema v3
"""

from datetime import date, datetime, timedelta
import logging
from typing import Optional
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from supabase import create_client, Client
from dotenv import load_dotenv
import os

try:
    from .budget_advisor import CategoryNotFoundError, assess_purchase
    from .knowledge_rag import KnowledgeBase, default_knowledge_path
except ImportError:  # Supports `python main.py` from the api directory.
    from budget_advisor import CategoryNotFoundError, assess_purchase
    from knowledge_rag import KnowledgeBase, default_knowledge_path

load_dotenv()

logger = logging.getLogger("expense_tracker.agent_activity")
logger.setLevel(logging.INFO)

# --- Supabase client ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Set SUPABASE_URL and SUPABASE_KEY in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Local knowledge base ---
# The path can be overridden with KNOWLEDGE_BASE_PATH. The default discovers
# the interview-prep Markdown file in the current workspace.
knowledge_base = KnowledgeBase(default_knowledge_path())

# --- App ---
app = FastAPI(
    title="Expense Tracker API",
    description="Personal expense & savings tracker — Star Schema v3",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic models ---
class TransactionCreate(BaseModel):
    transaction_date: date
    category_id: UUID
    amount: float = Field(gt=0)
    description: Optional[str] = None
    payment_method: str = "card"
    is_recurring: bool = False
    savings_goal_id: Optional[UUID] = None


class TransactionUpdate(BaseModel):
    transaction_date: Optional[date] = None
    category_id: Optional[UUID] = None
    amount: Optional[float] = Field(default=None, gt=0)
    description: Optional[str] = None
    payment_method: Optional[str] = None
    is_recurring: Optional[bool] = None
    savings_goal_id: Optional[UUID] = None


class BudgetCreate(BaseModel):
    type_id: UUID
    category_id: Optional[UUID] = None   # NULL = envelope budget for the entire type
    start_date: date
    budget_amount: float = Field(ge=0)
    # end_date defaults to '2030-01-01' in the DB (active). SCD Type 2: old rows get closed on update.


class SavingsGoalCreate(BaseModel):
    name: str
    target_amount: float = Field(gt=0)
    current_amount: float = 0
    target_date: Optional[date] = None


def sydney_today() -> date:
    return datetime.now(ZoneInfo("Australia/Sydney")).date()


class PurchaseAffordabilityRequest(BaseModel):
    item_name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0)
    category_name: str = Field(default="Shopping", min_length=1, max_length=50)
    purchase_date: date = Field(default_factory=sydney_today)
    warning_threshold: float = Field(default=0.90, ge=0.50, le=1.0)


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    top_k: int = Field(default=5, ge=1, le=10)
    min_score: float = Field(default=0.05, ge=0.0, le=1.0)


# --- Type endpoints (replaces expense-groups) ---
@app.get("/types")
def list_types():
    result = supabase.table("types").select("*").order("sort_order").execute()
    return result.data


# --- Category endpoints ---
@app.get("/categories")
def list_categories(type_id: Optional[str] = None):
    query = supabase.table("categories").select("*, types(name, sort_order)")
    if type_id:
        query = query.eq("type_id", type_id)
    result = query.order("name").execute()
    return result.data


# --- Transaction endpoints ---
@app.post("/transactions")
def create_transaction(txn: TransactionCreate):
    data = txn.model_dump(mode="json")
    data["category_id"] = str(data["category_id"])
    result = supabase.table("transactions").insert(data).execute()
    return result.data[0]


@app.get("/transactions")
def list_transactions(
    year: Optional[int] = None,
    month: Optional[int] = None,
    category_id: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0,
):
    query = supabase.table("transactions").select(
        "*, categories(name, type_id, types(name))"
    )

    if year and month:
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, month + 1, 1)
        query = query.gte("transaction_date", start.isoformat())
        query = query.lt("transaction_date", end.isoformat())

    if category_id:
        query = query.eq("category_id", category_id)

    result = (
        query.order("transaction_date", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data


@app.get("/transactions/{txn_id}")
def get_transaction(txn_id: UUID):
    result = (
        supabase.table("transactions")
        .select("*, categories(name, type_id, types(name))")
        .eq("id", str(txn_id))
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return result.data[0]


@app.put("/transactions/{txn_id}")
def update_transaction(txn_id: UUID, txn: TransactionUpdate):
    data = txn.model_dump(mode="json", exclude_none=True)
    if "category_id" in data:
        data["category_id"] = str(data["category_id"])
    result = (
        supabase.table("transactions")
        .update(data)
        .eq("id", str(txn_id))
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return result.data[0]


@app.delete("/transactions/{txn_id}")
def delete_transaction(txn_id: UUID):
    result = (
        supabase.table("transactions")
        .delete()
        .eq("id", str(txn_id))
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"status": "deleted"}


# --- Summary endpoints ---
@app.get("/summary/monthly")
def monthly_summary(year: int, month: int):
    result = (
        supabase.table("v_monthly_summary")
        .select("*")
        .eq("month", date(year, month, 1).isoformat())
        .execute()
    )
    return result.data


@app.get("/summary/savings-rate")
def savings_rate(year: Optional[int] = None):
    query = supabase.table("v_monthly_summary").select("*")
    result = (
        supabase.rpc(
            "get_savings_rate",
            {"p_year": year} if year else {},
        ).execute()
        if year
        else supabase.table("v_monthly_summary").select("*").execute()
    )
    return result.data


# --- Budget endpoints (unified — SCD Type 2 date-range versioning) ---
@app.post("/budgets")
def create_budget(budget: BudgetCreate):
    """Create or update a budget (SCD Type 2).
    - If category_id is set → per-category budget (e.g. Rent=$2200)
    - If category_id is null → envelope budget (e.g. variable=$1700)
    - On update: closes the active row (end_date=today) and inserts a new one.
    """
    type_id_str = str(budget.type_id)
    cat_id_str = str(budget.category_id) if budget.category_id else None

    # 1. Find the currently active row
    if cat_id_str:
        existing = supabase.table("budgets") \
            .select("id, budget_amount") \
            .eq("type_id", type_id_str) \
            .eq("category_id", cat_id_str) \
            .eq("end_date", "2030-01-01") \
            .execute()
    else:
        existing = supabase.table("budgets") \
            .select("id, budget_amount") \
            .eq("type_id", type_id_str) \
            .is_("category_id", "null") \
            .eq("end_date", "2030-01-01") \
            .execute()

    # 2. If same amount already exists, skip
    if existing.data and float(existing.data[0]["budget_amount"]) == budget.budget_amount:
        return existing.data[0]

    # 3. Close old active row (SCD Type 2)
    if existing.data:
        supabase.table("budgets") \
            .update({"end_date": date.today().isoformat()}) \
            .eq("id", existing.data[0]["id"]) \
            .execute()

    # 4. Insert new row (end_date defaults to '2030-01-01' in DB)
    data = {
        "type_id": type_id_str,
        "category_id": cat_id_str,
        "start_date": budget.start_date.isoformat(),
        "budget_amount": budget.budget_amount,
    }
    result = supabase.table("budgets").insert(data).execute()
    return result.data[0]


@app.get("/budgets")
def get_budgets(type_id: Optional[str] = None, include_history: bool = False):
    """Get current (or all) budgets.
    - include_history=false → only active budgets (end_date = '2030-01-01')
    - include_history=true  → all rows, including historical
    """
    query = supabase.table("budgets").select(
        "*, types(name), categories(name)"
    )
    if not include_history:
        query = query.eq("end_date", "2030-01-01")
    if type_id:
        query = query.eq("type_id", type_id)
    result = query.order("type_id").execute()
    return result.data


# --- Agentic budget advice ---
@app.post("/advice/can-i-afford")
def can_i_afford_purchase(request: PurchaseAffordabilityRequest):
    """Check whether a proposed purchase fits this month's applicable budget.

    The endpoint performs the financial calculation deterministically. An AI
    agent may call it and explain the result, but should not calculate or invent
    budget figures itself.
    """
    activity_id = str(uuid4())
    try:
        result = assess_purchase(
            supabase,
            item_name=request.item_name,
            price=request.price,
            category_name=request.category_name,
            purchase_date=request.purchase_date,
            warning_threshold=request.warning_threshold,
        )
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    result["activity_id"] = activity_id
    logger.info(
        "purchase_affordability_checked activity_id=%s category=%s decision=%s",
        activity_id,
        result["category"],
        result["decision"],
    )
    return result


# --- Merchant rule endpoints ---
class MerchantRuleCreate(BaseModel):
    keyword: str
    category_id: UUID
    priority: int = 0


@app.get("/merchant-rules")
def list_merchant_rules():
    result = supabase.table("merchant_rules") \
        .select("*, categories(name)") \
        .order("priority", desc=True) \
        .execute()
    return result.data


@app.post("/merchant-rules")
def create_merchant_rule(rule: MerchantRuleCreate):
    data = rule.model_dump(mode="json")
    data["category_id"] = str(data["category_id"])
    result = supabase.table("merchant_rules").upsert(data).execute()
    return result.data[0]


@app.delete("/merchant-rules/{rule_id}")
def delete_merchant_rule(rule_id: UUID):
    result = supabase.table("merchant_rules").delete().eq("id", str(rule_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"status": "deleted"}


# --- Pay date endpoints ---
class PayDateCreate(BaseModel):
    pay_date: date
    note: Optional[str] = None


@app.get("/pay-dates")
def list_pay_dates():
    result = supabase.table("pay_dates").select("*").order("pay_date").execute()
    return result.data


@app.post("/pay-dates")
def create_pay_date(pd: PayDateCreate):
    data = {"pay_date": pd.pay_date.isoformat(), "source": "manual", "note": pd.note}
    result = supabase.table("pay_dates").upsert(data).execute()
    return result.data[0]


@app.get("/pay-periods")
def list_pay_periods():
    """Derived pay periods from pay_dates."""
    result = supabase.table("v_pay_periods").select("*").order("period_start").execute()
    return result.data


@app.post("/pay-dates/detect")
def trigger_pay_detection():
    """Auto-detect salary deposits as pay dates."""
    salary_cat = supabase.table("categories").select("id").eq("name", "Salary").single().execute()
    if not salary_cat.data:
        raise HTTPException(status_code=404, detail="Salary category not found")

    salary_id = salary_cat.data["id"]
    txns = supabase.table("transactions") \
        .select("transaction_date") \
        .eq("category_id", salary_id) \
        .gte("amount", 3000) \
        .order("transaction_date") \
        .execute()

    inserted = 0
    skipped_near_confirmed = 0
    for row in txns.data:
        dt = row["transaction_date"]
        candidate = date.fromisoformat(dt)
        window_start = (candidate - timedelta(days=7)).isoformat()
        window_end = (candidate + timedelta(days=7)).isoformat()
        existing = (
            supabase.table("pay_dates")
            .select("pay_date,source")
            .gte("pay_date", window_start)
            .lte("pay_date", window_end)
            .execute()
        )
        if not existing.data:
            supabase.table("pay_dates").insert({
                "pay_date": dt, "source": "auto",
                "note": f"Detected from Salary transaction"
            }).execute()
            inserted += 1
        else:
            skipped_near_confirmed += 1

    return {
        "pay_dates_detected": inserted,
        "skipped_near_confirmed": skipped_near_confirmed,
        "total_salary_transactions": len(txns.data),
    }


# --- Savings goals endpoints ---
@app.post("/savings-goals")
def create_savings_goal(goal: SavingsGoalCreate):
    data = goal.model_dump(mode="json")
    result = supabase.table("savings_goals").insert(data).execute()
    return result.data[0]


@app.get("/savings-goals")
def list_savings_goals(status: str = "active"):
    result = (
        supabase.table("savings_goals")
        .select("*")
        .eq("status", status)
        .execute()
    )
    return result.data


@app.put("/savings-goals/{goal_id}")
def update_savings_goal(goal_id: UUID, current_amount: float):
    result = (
        supabase.table("savings_goals")
        .update({"current_amount": current_amount})
        .eq("id", str(goal_id))
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Goal not found")
    return result.data[0]


# --- Knowledge retrieval endpoints ---
@app.get("/knowledge/health")
def knowledge_health():
    """Report whether the interview knowledge source can be indexed."""
    try:
        return knowledge_base.status()
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/knowledge/search")
def search_knowledge(request: KnowledgeSearchRequest):
    """Retrieve cited knowledge chunks for the Foundry agent or UI."""
    try:
        matches = knowledge_base.search(
            request.query,
            top_k=request.top_k,
            min_score=request.min_score,
        )
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "query": request.query,
        "source_path": str(knowledge_base.source_path),
        "matches": [match.as_dict() for match in matches],
    }


# --- Health check ---
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
