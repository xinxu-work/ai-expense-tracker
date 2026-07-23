"""
Expense Tracker AI Agent — MS Foundry + Supabase
=================================================
Deployable function-calling agent that connects a Foundry-hosted LLM
to your Supabase expense tracker database.

Architecture:
  Purchase advice: User -> Foundry Agent -> FastAPI -> Supabase -> Reply
  Legacy read tools: User -> Foundry Agent -> Supabase -> Reply

Usage:
  1. Set environment variables (or create .env):
     FOUNDRY_PROJECT_ENDPOINT=https://<resource>.ai.azure.com/api/projects/<project>
     FOUNDRY_MODEL_DEPLOYMENT=<your-model-deployment-name>
     SUPABASE_URL=https://<project>.supabase.co
     SUPABASE_KEY=eyJ...  (anon/service key)

  2. az login   (authenticate to Azure)

  3. python foundry_agent.py

Prerequisites:
  pip install azure-ai-projects azure-identity supabase python-dotenv
"""

import json, os, sys
from datetime import date, datetime, timedelta
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv(os.path.join(os.path.dirname(__file__), "api", ".env"))

FOUNDRY_ENDPOINT = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
FOUNDRY_MODEL_DEPLOYMENT = os.getenv("FOUNDRY_MODEL_DEPLOYMENT")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
EXPENSE_API_URL = os.getenv("EXPENSE_API_URL", "http://localhost:8000")

if not all([FOUNDRY_ENDPOINT, FOUNDRY_MODEL_DEPLOYMENT, SUPABASE_URL, SUPABASE_KEY]):
    print("ERROR: Missing environment variables.")
    print("  Required: FOUNDRY_PROJECT_ENDPOINT, FOUNDRY_MODEL_DEPLOYMENT, SUPABASE_URL, SUPABASE_KEY")
    print("  Tip: put SUPABASE_URL + SUPABASE_KEY in api/.env")
    print("       set FOUNDRY_PROJECT_ENDPOINT in your terminal or .env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------------------------------------------------------
# Tool Functions — Supabase queries exposed to the LLM
# ---------------------------------------------------------------------------

def _query_to_json(result, key: str = "data") -> str:
    """Helper: convert Supabase result to JSON string for the agent."""
    return json.dumps(result.data, default=str)


def _month_bounds(year_month: str) -> tuple[date, date]:
    """Parse YYYY-MM and return an inclusive start and exclusive end."""
    start = datetime.strptime(year_month, "%Y-%m").date().replace(day=1)
    end = (
        date(start.year + 1, 1, 1)
        if start.month == 12
        else date(start.year, start.month + 1, 1)
    )
    return start, end


def get_monthly_spending(
    year_month: str,
    category_name: Optional[str] = None,
) -> str:
    """
    Get total spending per category for a given month (YYYY-MM).
    Optionally filter to a single category.
    """
    start, end = _month_bounds(year_month)
    query = (
        supabase.table("transactions")
        .select("amount, transaction_date, description, categories!inner(name)")
        .gte("transaction_date", start.isoformat())
        .lt("transaction_date", end.isoformat())
    )
    if category_name:
        query = query.eq("categories.name", category_name)

    result = query.execute()

    if not result.data:
        return json.dumps({"message": f"No transactions found for {year_month}"})

    by_category = {}
    for row in result.data:
        cat = row["categories"]["name"]
        amt = float(row["amount"])
        by_category.setdefault(cat, {"total": 0.0, "count": 0})
        by_category[cat]["total"] += amt
        by_category[cat]["count"] += 1

    return json.dumps({
        "month": year_month,
        "categories": {
            k: {"total": round(v["total"], 2), "transaction_count": v["count"]}
            for k, v in sorted(by_category.items(), key=lambda x: x[1]["total"], reverse=True)
        }
    })


def get_budget_status(year_month: str) -> str:
    """
    Get budget vs actual spending for a given month.
    Compares budgets table to actual transaction spending.
    """
    start, end = _month_bounds(year_month)
    today_sydney = datetime.now(ZoneInfo("Australia/Sydney")).date()
    if start <= today_sydney < end:
        reference_day = today_sydney
    elif end <= today_sydney:
        reference_day = end - timedelta(days=1)
    else:
        reference_day = start

    # Load budgets applicable to the requested period. Category budgets apply
    # to one category; envelope budgets apply to every category of that type.
    budgets = (
        supabase.table("budgets")
        .select(
            "id,type_id,category_id,start_date,end_date,budget_amount,"
            "categories(name),types!inner(name)"
        )
        .lte("start_date", reference_day.isoformat())
        .gt("end_date", reference_day.isoformat())
        .execute()
    )

    if not budgets.data:
        return json.dumps({"message": f"No budgets set for {year_month}"})

    results = []
    for b in budgets.data:
        budget_amt = float(b["budget_amount"])
        category = b.get("categories")
        type_name = b["types"]["name"]
        budget_scope = "category" if b.get("category_id") else "type_envelope"
        budget_name = category["name"] if category else f"{type_name} envelope"

        actual_query = (
            supabase.table("transactions")
            .select("amount,categories!inner(type_id)")
            .gte("transaction_date", start.isoformat())
            .lt("transaction_date", end.isoformat())
        )
        if b.get("category_id"):
            actual_query = actual_query.eq("category_id", b["category_id"])
        else:
            actual_query = actual_query.eq("categories.type_id", b["type_id"])
        actual = actual_query.execute()
        actual_amt = sum(float(r["amount"]) for r in actual.data)

        pct = round((actual_amt / budget_amt) * 100, 1) if budget_amt > 0 else 0
        status = "over_budget" if actual_amt > budget_amt else (
            "near_budget" if actual_amt > budget_amt * 0.9 else "on_track"
        )
        results.append({
            "budget_name": budget_name,
            "budget_scope": budget_scope,
            "type": type_name,
            "budget": budget_amt,
            "actual": round(actual_amt, 2),
            "utilisation_pct": pct,
            "status": status,
        })

    return json.dumps({"month": year_month, "budgets": results})


def get_monthly_summary(year_month: str) -> str:
    """
    Get income vs expenses vs savings summary for a given month.
    Returns totals by type (income/expense/saving).
    """
    start, end = _month_bounds(year_month)
    result = (
        supabase.table("transactions")
        .select("amount, categories!inner(type_id, types!inner(name))")
        .gte("transaction_date", start.isoformat())
        .lt("transaction_date", end.isoformat())
        .execute()
    )

    if not result.data:
        return json.dumps({"message": f"No transactions for {year_month}"})

    totals = {"income": 0.0, "expense": 0.0, "saving": 0.0}
    for row in result.data:
        amt = float(row["amount"])
        type_name = row["categories"]["types"]["name"]
        if type_name in ("fixed", "variable"):
            totals["expense"] += amt
        elif type_name == "income":
            totals["income"] += amt
        elif type_name == "saving":
            totals["saving"] += amt

    net = totals["income"] - totals["expense"]
    savings_rate = round((net / totals["income"]) * 100, 1) if totals["income"] > 0 else 0

    return json.dumps({
        "month": year_month,
        "total_income": round(totals["income"], 2),
        "total_expenses": round(totals["expense"], 2),
        "total_savings": round(totals["saving"], 2),
        "net_after_expenses": round(net, 2),
        "remaining_after_savings": round(net - totals["saving"], 2),
        "savings_rate_pct": savings_rate,
    })


def list_categories(type_filter: Optional[str] = None) -> str:
    """
    List all expense categories. Optionally filter by type:
    'fixed', 'variable', 'income', or 'saving'.
    """
    query = supabase.table("categories").select("name, types!inner(name, sort_order)")
    if type_filter:
        query = query.eq("types.name", type_filter)
    result = query.order("types(sort_order),name").execute()

    by_type = {}
    for row in result.data:
        tname = row["types"]["name"]
        by_type.setdefault(tname, []).append(row["name"])

    return json.dumps({"categories": by_type})


def search_transactions(query_text: str, limit: int = 10) -> str:
    """
    Search transactions by description text (case-insensitive partial match).
    """
    result = (
        supabase.table("transactions")
        .select("transaction_date, amount, description, categories(name)")
        .ilike("description", f"%{query_text}%")
        .order("transaction_date", desc=True)
        .limit(limit)
        .execute()
    )

    if not result.data:
        return json.dumps({"message": f"No transactions matching '{query_text}'"})

    return json.dumps({
        "search": query_text,
        "results": [
            {
                "date": r["transaction_date"],
                "amount": float(r["amount"]),
                "category": r["categories"]["name"],
                "description": r.get("description", ""),
            }
            for r in result.data
        ]
    }, default=str)


def check_purchase_affordability(
    item_name: str,
    price: float,
    category_name: str = "Shopping",
    purchase_date: Optional[str] = None,
) -> str:
    """Check whether a proposed purchase fits the applicable monthly budget.

    This tool intentionally calls the FastAPI business layer instead of letting
    the model reproduce financial rules or query/write the database directly.
    """
    payload = {
        "item_name": item_name,
        "price": price,
        "category_name": category_name,
    }
    if purchase_date:
        payload["purchase_date"] = purchase_date

    endpoint = urljoin(EXPENSE_API_URL.rstrip("/") + "/", "advice/can-i-afford")
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            return response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return json.dumps({
            "error": "expense_api_rejected_request",
            "status_code": exc.code,
            "detail": body,
        })
    except URLError as exc:
        return json.dumps({
            "error": "expense_api_unavailable",
            "detail": str(exc.reason),
            "hint": f"Start FastAPI at {EXPENSE_API_URL} before using this tool.",
        })


def retrieve_knowledge(query: str, top_k: int = 5) -> str:
    """Retrieve cited chunks from the connected interview knowledge base."""
    endpoint = urljoin(EXPENSE_API_URL.rstrip("/") + "/", "knowledge/search")
    payload = {"query": query, "top_k": top_k}
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            return response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return json.dumps({
            "error": "knowledge_search_rejected_request",
            "status_code": exc.code,
            "detail": body,
        })
    except URLError as exc:
        return json.dumps({
            "error": "expense_api_unavailable",
            "detail": str(exc.reason),
            "hint": f"Start FastAPI at {EXPENSE_API_URL} before using this tool.",
        })

# ---------------------------------------------------------------------------
# Tool registry — register every function as a Foundry tool
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "function": get_monthly_spending,
        "name": "get_monthly_spending",
        "description": "Get total spending by category for a specific month (YYYY-MM format). Use this when asked about spending in a month, or spending on a specific category.",
        "parameters": {
            "type": "object",
            "properties": {
                "year_month": {"type": "string", "description": "Month in YYYY-MM format, e.g. '2026-03'"},
                "category_name": {"type": "string", "description": "Optional: filter to a single category name, e.g. 'Groceries'"},
            },
            "required": ["year_month"],
            "additionalProperties": False,
        },
    },
    {
        "function": get_budget_status,
        "name": "get_budget_status",
        "description": "Compare budget vs actual spending for a month. Shows each category's budget, actual spend, and whether it's over/under budget.",
        "parameters": {
            "type": "object",
            "properties": {
                "year_month": {"type": "string", "description": "Month in YYYY-MM format, e.g. '2026-04'"},
            },
            "required": ["year_month"],
            "additionalProperties": False,
        },
    },
    {
        "function": get_monthly_summary,
        "name": "get_monthly_summary",
        "description": "Get income vs expenses vs savings summary for a month. Shows total income, total expenses, total savings, net amount, and savings rate percentage.",
        "parameters": {
            "type": "object",
            "properties": {
                "year_month": {"type": "string", "description": "Month in YYYY-MM format, e.g. '2026-03'"},
            },
            "required": ["year_month"],
            "additionalProperties": False,
        },
    },
    {
        "function": list_categories,
        "name": "list_categories",
        "description": "List all expense categories grouped by type (fixed, variable, income, saving). Use this when the user asks what categories exist.",
        "parameters": {
            "type": "object",
            "properties": {
                "type_filter": {"type": "string", "description": "Optional: filter to one type: 'fixed', 'variable', 'income', or 'saving'"},
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "function": search_transactions,
        "name": "search_transactions",
        "description": "Search transactions by description text. Use when the user asks about a specific purchase or merchant.",
        "parameters": {
            "type": "object",
            "properties": {
                "query_text": {"type": "string", "description": "Text to search for in transaction descriptions, e.g. 'Woolworths' or 'rent'"},
                "limit": {"type": "integer", "description": "Max results to return (default 10)"},
            },
            "required": ["query_text"],
            "additionalProperties": False,
        },
    },
    {
        "function": check_purchase_affordability,
        "name": "check_purchase_affordability",
        "description": (
            "Check whether a proposed purchase fits the user's applicable monthly "
            "budget after including spending already recorded this month. Use this "
            "for questions such as 'Can I afford $150 shoes this month?'"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "item_name": {
                    "type": "string",
                    "description": "The item the user is considering, e.g. 'running shoes'",
                },
                "price": {
                    "type": "number",
                    "description": "Proposed purchase price in AUD",
                },
                "category_name": {
                    "type": "string",
                    "description": "Expense category. Use 'Shopping' for shoes and clothing.",
                },
                "purchase_date": {
                    "type": "string",
                    "description": "Optional purchase date in YYYY-MM-DD format",
                },
            },
            "required": ["item_name", "price", "category_name"],
            "additionalProperties": False,
        },
    },
    {
        "function": retrieve_knowledge,
        "name": "retrieve_knowledge",
        "description": (
            "Retrieve relevant, cited passages from the connected knowledge base. "
            "Use for interview notes, budgeting rules, documented explanations, "
            "and other unstructured knowledge. Do not use this to calculate "
            "transaction totals, budgets, or affordability."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The question or topic to search for",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of evidence chunks to return, from 1 to 10",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
]

# Build FunctionTool objects and dispatch map
tools: list[FunctionTool] = []
dispatch = {}

for t in TOOL_DEFINITIONS:
    ft = FunctionTool(
        name=t["name"],
        parameters=t["parameters"],
        description=t["description"],
        strict=True,
    )
    tools.append(ft)
    dispatch[t["name"]] = t["function"]

# ---------------------------------------------------------------------------
# Agent setup + chat loop
# ---------------------------------------------------------------------------

def create_agent(project: AIProjectClient):
    """Create (or recreate) the expense tracker agent. Deletes old version first."""
    agent_name = "ExpenseTrackerAssistant"

    # Delete existing version so we can recreate with updated tools
    try:
        versions = project.agents.list_versions(agent_name)
        for v in (versions or []):
            project.agents.delete_version(agent_name, v["version"])
    except Exception:
        pass  # doesn't exist yet

    today_sydney = datetime.now(ZoneInfo("Australia/Sydney")).date()
    agent = project.agents.create_version(
        agent_name=agent_name,
        definition=PromptAgentDefinition(
            model=FOUNDRY_MODEL_DEPLOYMENT,
            instructions=(
                "You are a personal finance assistant with access to the user's expense tracker database. "
                "Use the provided function tools to answer questions about their spending, budget, savings, "
                "and transactions. Always present amounts with a dollar sign and round to two decimal places. "
                "Use retrieve_knowledge for documented interview knowledge, budgeting rules, and explanations; "
                "when using it, cite the returned source and do not invent unsupported information. "
                "When comparing budget vs actual, highlight categories that are over or near budget. "
                "For proposed purchases, always call check_purchase_affordability; do not estimate or "
                "calculate affordability yourself. Explain whether it is within budget, tight, over "
                "budget, or cannot be assessed because no budget exists. Make clear that fitting a "
                "budget is not the same as confirming available cash or giving financial advice. "
                "Provide helpful financial insights based on the data — e.g., trends, suggestions, or patterns. "
                f"Be conversational and supportive. Today's date in Australia/Sydney is {today_sydney.isoformat()}."
            ),
            tools=tools,
        ),
    )
    print(f"Agent created: {agent.name} v{agent.version}")
    return agent


def main():
    print("=" * 60)
    print(" EXPENSE TRACKER AI AGENT (MS Foundry + Supabase)")
    print("=" * 60)

    # 1. Connect to Foundry
    print(f"\nConnecting to Foundry...")
    project = AIProjectClient(
        endpoint=FOUNDRY_ENDPOINT,
        credential=DefaultAzureCredential(),
    )
    print(f"  OK — {FOUNDRY_ENDPOINT}")

    # 2. Verify Supabase
    try:
        test = supabase.table("categories").select("count", count="exact").execute()
        print(f"  Supabase OK — {test.count} categories")
    except Exception as e:
        print(f"  Supabase ERROR: {e}")
        sys.exit(1)

    # 3. Create agent
    print(f"\nCreating agent with {len(tools)} tools:")
    for t in TOOL_DEFINITIONS:
        print(f"  - {t['name']}: {t['description'][:80]}...")
    agent = create_agent(project)

    # 4. Chat loop
    openai_client = project.get_openai_client()
    conversation = openai_client.conversations.create()

    print("\n" + "=" * 60)
    print(" Chat ready. Try:")
    print("   'How much did I spend in March?'")
    print("   'Am I over budget this month?'")
    print("   'What's my savings rate for April?'")
    print("   'Search for Woolworths transactions'")
    print("   'List all my categories'")
    print("   'Can I buy a $150 pair of shoes this month?'")
    print(" Type 'exit' to quit.")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if user_input.lower() in ("exit", "quit", "q"):
            print("Goodbye!")
            break
        if not user_input:
            continue

        # Send to agent
        response = openai_client.responses.create(
            input=user_input,
            conversation=conversation.id,
            extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
        )

        # Handle function calls
        max_loops = 5  # safety: prevent infinite tool loops
        for _ in range(max_loops):
            tool_outputs = []
            for item in response.output:
                if item.type == "function_call":
                    func = dispatch.get(item.name)
                    if func:
                        args = json.loads(item.arguments)
                        print(f"  [tool] {item.name}({args})")
                        result = func(**args)
                        tool_outputs.append({
                            "type": "function_call_output",
                            "call_id": item.call_id,
                            "output": result,
                        })
                    else:
                        print(f"  [tool] UNKNOWN: {item.name}")

            if not tool_outputs:
                break  # no more function calls → final answer ready

            # Submit results and loop for potential follow-up calls
            response = openai_client.responses.create(
                input=tool_outputs,
                conversation=conversation.id,
                extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
            )

        # Print final response
        print(f"\nAgent: {response.output_text}")

    # 5. Cleanup
    print("\nCleaning up...")
    try:
        project.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
        openai_client.conversations.delete(conversation_id=conversation.id)
    except Exception:
        pass
    print("Done.")


if __name__ == "__main__":
    main()
