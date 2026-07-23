# Expense Tracker - Full Data Pipeline

Personal expense & savings tracker with a modern data and agentic AI stack:
**Supabase -> dbt -> FastAPI -> Microsoft Foundry Agent -> Power BI**

---

## Architecture

```
Data Entry (API / Supabase UI)
        |
   Supabase (PostgreSQL)
        |
   dbt Core (transform)
        |
   Mart Tables + FastAPI business tools
        |                       |
   Power BI dashboard     Microsoft Foundry Agent
                                  |
                        Purchase budget advice
```

---

## 1. Supabase Setup

### Create Project
1. Go to https://supabase.com and create a free account
2. Create a new project (pick a region close to Australia)
3. Note your **Project URL** and **anon key** from Settings > API

### Run Schema
1. Go to **SQL Editor** in the Supabase dashboard
2. Paste the contents of `supabase_schema.sql`
3. Click **Run** — this creates all tables, indexes, views, and seed data

### Get Connection Details (for dbt & Power BI)
- Go to **Settings > Database**
- Note: Host, Port (5432), Database (postgres), User (postgres), Password

---

## 2. FastAPI Setup

```bash
cd api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Supabase URL and anon key

# Run the API
python main.py
```

API runs at http://localhost:8000

- Interactive docs: http://localhost:8000/docs
- Endpoints: `/transactions`, `/categories`, `/budgets`, `/savings-goals`, `/summary/monthly`, `/advice/can-i-afford`

### Purchase affordability endpoint

The endpoint checks a proposed purchase against either its category budget or,
when no category budget exists, the category's type-level envelope budget.
Shoes use the seeded `Shopping` category and the shared `variable` envelope.

```bash
curl -X POST http://localhost:8000/advice/can-i-afford \
  -H "Content-Type: application/json" \
  -d '{"item_name":"running shoes","price":150,"category_name":"Shopping"}'
```

The deterministic response includes current-month spending, remaining budget,
projected utilisation, an `activity_id`, and one of four decisions:
`within_budget`, `tight`, `over_budget`, or `no_budget`.

---

## 3. Microsoft Foundry Agent

Keep the FastAPI service running, then configure `api/.env` from
`api/.env.example` and install the agent dependencies:

```bash
pip install -r requirements-agent.txt
az login
python foundry_agent.py
```

For a new tenant, set `FOUNDRY_PROJECT_ENDPOINT` to the new Foundry project and
`FOUNDRY_MODEL_DEPLOYMENT` to an available model deployment in that project.
The model name is configuration rather than a hard-coded dependency.

Example question:

> I want to buy a $150 pair of running shoes. Does it fit this month's budget?

The Foundry agent calls `POST /advice/can-i-afford` and explains the API's
calculation. It is instructed not to estimate affordability itself and to state
that fitting a budget does not prove cash availability or constitute financial
advice.

---

## 4. dbt Setup

### Install dbt
```bash
pip install dbt-postgres
```

### Configure Connection
Copy `dbt_expense_tracker/profiles.yml` to `~/.dbt/profiles.yml` and update with your Supabase credentials.

### Run dbt
```bash
cd dbt_expense_tracker

# Test connection
dbt debug

# Run all models
dbt run

# Optional: use standard calendar months instead of salary pay periods
dbt run --vars '{period_mode: calendar}'

# Run tests
dbt test

# Generate docs
dbt docs generate
dbt docs serve
```

The default `period_mode` is `payday`. It assigns each transaction to the
period beginning on a confirmed salary date and ending the day before the next
salary date. Calendar mode uses the first through last day of each month and
does not require removing or disabling the `pay_dates` table.

### dbt Model Lineage
```
sources (raw tables)
    |
staging (stg_transactions, stg_categories)
    |-- AEST date conversion
    |-- Type casting & cleaning
    |
marts
    |-- fct_monthly_summary     (spending by category per month, YTD)
    |-- fct_savings_rate        (income vs expenses, savings %, 3-month rolling avg)
    |-- fct_budget_vs_actual    (budget utilisation, over/under flags)
```

---

## 5. Power BI Connection

### Connect to Supabase PostgreSQL

1. Open Power BI Desktop
2. **Get Data** > **PostgreSQL database**
3. Enter connection details:
   - Server: `db.YOUR_PROJECT_ID.supabase.co`
   - Database: `postgres`
   - Data Connectivity mode: **DirectQuery** (for live data) or **Import**
4. Enter credentials: User `postgres`, Password from Supabase dashboard
5. Select the mart tables:
   - `fct_monthly_summary`
   - `fct_savings_rate`
   - `fct_budget_vs_actual`

### Suggested Dashboard Pages

**Page 1: Monthly Overview**
- Card visuals: Total Income, Total Expenses, Net Savings, Savings Rate %
- Bar chart: Spending by category (current month)
- Line chart: Monthly spending trend (last 12 months)

**Page 2: Budget Tracker**
- Gauge visuals: Budget utilisation per category
- Table: Budget vs Actual with conditional formatting (red = over budget)
- Slicer: Month/Year selector

**Page 3: Savings Progress**
- KPI visual: Savings rate % vs target
- Line chart: 3-month rolling average income vs expenses
- Progress bars: Savings goals completion

### Power BI Tips
- Use **DirectQuery** if you want real-time data from Supabase
- Use **Import** mode if you want faster performance (schedule refresh)
- Date columns are already AEST-converted in the dbt models

---

## 6. Future Enhancements (Phase 2+)

- [ ] AI-powered transaction categorisation (Claude API)
- [ ] Auto-import from bank CSV/OFX files
- [ ] Hybrid RAG for budgeting rules, receipts, statements, and personal finance notes
- [ ] Multi-tenant support for customer deployments
- [ ] Airflow orchestration for scheduled dbt runs
- [ ] Industry templates (restaurant, retail)
- [ ] Onboard the Foundry agent to Agent 365 for enterprise identity,
      governance, monitoring, and lifecycle management

Agent 365 is deliberately excluded from the personal prototype's runtime. See
[`docs/agent-365-governance-roadmap.md`](docs/agent-365-governance-roadmap.md)
for the future adoption design.

See [`docs/rag-development-plan.md`](docs/rag-development-plan.md) for the
hybrid RAG architecture, delivery phases, data model, evaluation criteria, and
production governance plan.

### RAG learning slice

The first hands-on RAG slice uses the interview knowledge base stored at
`DS/Interview_Prep/AI_Engineer_Knowledge_QA.md`. Start FastAPI, then use:

```bash
curl http://localhost:8000/knowledge/health

curl -X POST http://localhost:8000/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{"query":"How do I evaluate a production RAG application?","top_k":3}'
```

The endpoint returns question-level chunks with source line citations. This
first learning slice uses dependency-free TF-IDF retrieval so it can run
without an embedding API or vector database. The Foundry agent exposes the
same capability through `retrieve_knowledge`; exact financial questions
continue to use the existing structured tools. The next production upgrade is
to replace the local retriever with dense embeddings and a vector index.

---

## Project Structure

```
expense_tracker/
|-- supabase_schema.sql          # Database schema (run in Supabase SQL Editor)
|-- foundry_agent.py             # Foundry chat agent and tool dispatch
|-- requirements-agent.txt       # Foundry agent dependencies
|-- docs/
|   |-- rag-development-plan.md
|   |-- agent-365-governance-roadmap.md
|-- api/
|   |-- main.py                  # FastAPI backend
|   |-- budget_advisor.py        # Deterministic purchase budget rules
|   |-- knowledge_rag.py         # Citation-preserving local knowledge retrieval
|   |-- requirements.txt         # Python dependencies
|   |-- .env.example             # Environment template
|   |-- tests/
|       |-- test_budget_advisor.py
|       |-- test_knowledge_rag.py
|-- dbt_expense_tracker/
|   |-- dbt_project.yml          # dbt config
|   |-- profiles.yml             # DB connection (copy to ~/.dbt/)
|   |-- models/
|       |-- staging/
|       |   |-- stg_transactions.sql
|       |   |-- stg_categories.sql
|       |   |-- schema.yml
|       |-- marts/
|           |-- fct_monthly_summary.sql
|           |-- fct_savings_rate.sql
|           |-- fct_budget_vs_actual.sql
|           |-- schema.yml
```
