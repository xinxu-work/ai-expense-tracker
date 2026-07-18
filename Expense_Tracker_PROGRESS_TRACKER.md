# Expense Tracker — Project Notes

Last updated: 2026-06-13

## Vision

A personal expense/savings tracker that evolves into an AI-powered SaaS for retail/restaurant owners.

- **Phase 1 (current)** — Personal tracker: Supabase + FastAPI + dbt + Power BI
- **Phase 2** — AI data transformation pipeline for customer CSV/Excel uploads (auto-clean, auto-map to standard schema)
- **Phase 3** — Customer-facing SaaS for non-technical users (web upload → auto dashboard)

## Stack

| Layer | Tool |
|---|---|
| Database | Supabase (PostgreSQL, project ref `meluzsqwjzrsmmhimtpk`) |
| API | FastAPI + Pydantic + Supabase Python client |
| Transformation | dbt (staging → marts) |
| BI | Power BI (PostgreSQL connector) |
| Repo | GitHub: `xinxu-work/DS` (public monorepo) |

## dbt — Transformation Layer

### What dbt Is

dbt (data build tool) is the "T" in ELT — it transforms raw data into analytics tables using only SQL. Instead of moving data out of the database for transformation (ETL), dbt sends SQL to Supabase, which runs it inside PostgreSQL. Zero data movement, zero infrastructure.

### ELT Process (Extract → Load → Transform)

```
1. EXTRACT + LOAD         2. TRANSFORM (dbt)
   (one step)                (inside Supabase)
┌──────────────────┐    ┌─────────────────────────┐
│ Python reads Excel│    │ dbt sends SQL to        │
│ Maps columns      │───►│ Supabase PostgreSQL     │
│ Inserts via       │    │                         │
│ Supabase REST API │    │ staging/ (VIEWS)        │
│                   │    │  stg_transactions       │
│ Raw data lands    │    │  stg_categories         │
│ in public.* tables│    │                         │
└──────────────────┘    │ marts/ (TABLES)          │
                         │  fct_monthly_summary     │
                         │  fct_savings_rate        │
                         │  fct_budget_vs_actual    │
                         │  fct_expense_group_summary│
                         └─────────────────────────┘
                                    │
                                    ▼
                            Power BI reads
                            marts.* tables
```

### The 5 Models

| Model | Type | What It Produces |
|---|---|---|
| `stg_transactions` | Staging (view) | Cleaned transactions + AEST timezone + year/month/day columns |
| `stg_categories` | Staging (view) | Standardized category names with expense_group |
| `fct_monthly_summary` | Mart (table) | Spending by category/month + YTD running totals |
| `fct_savings_rate` | Mart (table) | Income vs expenses vs savings rate + 3-month rolling avg |
| `fct_budget_vs_actual` | Mart (table) | Category-level budget utilization with over/under flags |
| `fct_expense_group_summary` | Mart (table) | Fixed vs variable group budget with status indicators |

### Key dbt Concepts

- **`{{ source('expense_tracker', 'transactions') }}`** — references raw Supabase tables
- **`{{ ref('stg_transactions') }}`** — references another dbt model; dbt auto-resolves run order
- **Lineage is automatic** — dbt knows `fct_monthly_summary` depends on `stg_transactions` and runs them in order
- **Views for staging** (always fresh, no storage), **tables for marts** (pre-built, fast Power BI queries)
- **`dbt run`** — single command compiles and executes all models in dependency order

### Cross-Platform Portability

All 6 dbt models are database-agnostic Jinja + SQL. Only `profiles.yml` changes between platforms.

### AWS RDS Migration Path

Supabase runs on AWS under the hood (Singapore `ap-southeast-1`). Migrating to self-managed AWS RDS for PostgreSQL is a straightforward lift-and-shift:

| Layer | Supabase (current) | AWS RDS (future) |
|---|---|---|
| PostgreSQL | Managed by Supabase | RDS for PostgreSQL / Aurora |
| Connection pooler | Supavisor (AWS-1 pooler) | RDS Proxy |
| REST API | FastAPI on any host | Same, on EC2 / ECS Fargate / Lambda |
| Auth | Supabase anon key | IAM or Cognito |
| BI | Power BI | Same — no change |
| Cost | Free tier | ~$15-20/month (db.t4g.micro) |

**Migration steps:**
1. `pg_dump` from Supabase → `pg_restore` to RDS (via IPv4 add-on or pooler)
2. Update `profiles.yml` — change host/port only
3. Run `dbt run` — all models rebuild identically on RDS
4. Repoint Power BI to new RDS endpoint
5. Deploy FastAPI via ECS Fargate or Lambda function URL

**profiles.yml change (one file):**
```yaml
# Supabase
host: aws-1-ap-southeast-1.pooler.supabase.com
user: postgres.meluzsqwjzrsmmhimtpk

# AWS RDS
host: my-tracker.xxxx.ap-southeast-2.rds.amazonaws.com
user: postgres
```

**When to migrate:** Paying customers, VPC isolation, IAM auth, compliance needs (SOC2, HIPAA). For personal use, portfolio, and early SaaS — Supabase is the right choice.

### RDS vs Redshift: Which One?

These serve different roles in the architecture. For this project, the answer is clear:

| | RDS (PostgreSQL) | Redshift |
|---|---|---|
| **Role** | Transactional (OLTP) | Analytical (OLAP) |
| **Purpose** | Store transactions, run CRUD via FastAPI | Data warehouse for massive queries |
| **dbt** | ✅ Runs here — staging + marts | ✅ Can run here — overkill at small scale |
| **Power BI** | ✅ DirectQuery or Import | ✅ Ideal at scale (columnar, billions of rows) |
| **Row count** | Ideal for < 10M rows | Shines at 100M+ rows |
| **Storage** | Row-based | Columnar (compresses well) |
| **Cost** | ~$15/month (micro) | ~$200+/month minimum |
| **Project fit** | **✅ Right now** | Phase 3+ only |

**Recommended AWS architecture by phase:**

```
Phase 1-2 (now → early SaaS):
  FastAPI → RDS PostgreSQL (single source of truth)
            │
            ├── dbt runs inside RDS (staging + marts)
            │
            └── Power BI connects to RDS

Phase 3 (hundreds of customers, millions of rows):
  FastAPI → RDS PostgreSQL (transactions)
            │
            ├── dbt on Redshift (analytics marts)
            │
            └── Power BI connects to Redshift
```

**Why not start on Redshift?** 27 rows don't need a columnar warehouse. Redshift has a ~$200/month floor, requires cluster management, and adds latency for the transactional CRUD that FastAPI needs. Start on RDS; add Redshift when query times degrade or you need separation of operational and analytical workloads.

## Repo

- Originally started as standalone `xinxu-work/finflow-ai`, later consolidated into the DS monorepo for portfolio cohesion
- Local path: `c:\Users\XinXu\iCloudDrive\Xin_Xin_File\DS\Learning\AI_Practice\expense_tracker`
- Remote: https://github.com/xinxu-work/DS
- Default branch: `main` (local + remote in sync)
- Commit author: `xinxu-work <256224852+xinxu-work@users.noreply.github.com>` (per-repo config)

## Related Work & Background

**Microsoft Fabric / Synapse** (`MS/TEEG/`)
- TEEG CID project: production data platform ingesting Dynamics 365 / Dataverse
- 60+ Synapse Spark notebooks, Bronze → Silver Lakehouse architecture
- CI/CD pipelines (Azure DevOps YAML), semantic models, managed VNets
- AEST timezone conversion patterns reused in dbt models

**Databricks AI Agents** (`Conference/Databricks/`)
- Databricks AI Days conference — full course on Mosaic AI agents
- Built ToolCallingAgent via MLflow `ResponsesAgent` + `databricks-gpt-5-4`
- Tools: vector search (`search_product_docs`), UC functions (`get_return_policy`)
- Agent evaluation with MLflow scorers, deployment to Unity Catalog
- Exported 3 agent sessions with driver notebooks + `agent.py`

**Pattern reuse in this project:** Databricks Unity Catalog functions → Python `agent_tools.py` functions. Databricks model serving → FastAPI `/chat` endpoint.

## Database Schema (current — Star Schema v3)

### Tables (6)

| Table | PK | Role | Key FKs |
|---|---|---|---|
| `dim_date` | `date` | Date dimension | — |
| `types` | `id` | Type dimension (fixed, variable, income, saving) | — |
| `categories` | `id` | Category dimension (22 rows) | `type_id` → `types.id` |
| `transactions` | `id` | **FACT table** | `transaction_date` → `dim_date.date`, `category_id` → `categories.id`, `savings_goal_id` → `savings_goals.id` |
| `budgets` | `id` | Unified budget table (SCD Type 2) | `type_id` → `types.id`, `category_id` → `categories.id` (nullable), `start_date` + `end_date` date-range versioning |
| `savings_goals` | `id` | Savings targets | — |

### Star Schema Diagram

```
dim_date ──► transactions ◄── categories ◄── types
                │
                ├── savings_goals
                │
                └── budgets ◄── types
                      └── categories (nullable: NULL = envelope budget)
```

- Fixed budgets: `budgets.category_id IS NOT NULL` → per-category (e.g. Rent=$2200)
- Variable budget: `budgets.category_id IS NULL` → envelope budget for the type (e.g. variable=$1700)
- **SCD Type 2**: `start_date` + `end_date` date-range versioning; `end_date = '2030-01-01'` = active
- Transactions are the single fact table linking to all dimensions
- `dim_date` provides calendar + fiscal period attributes (15th-to-15th cycle)
- `savings_goals` linked via nullable FK — only savings deposits link to a goal

### Fiscal Period Logic (in dim_date)

The user's salary arrives mid-month (14th). Each fiscal period spans the 14th to the 13th of the next month:
- `fiscal_month_label` = YYYY-MM of the period (e.g., March 14 - April 13 = "2026-03")
- Calculated by shifting date back 13 days, then extracting month

## Product Architecture (Phase 2-3 Vision)

### Customer Upload Flow
```
Customer's CSV/Excel → AI Cleaner (Claude API) → Supabase → dbt → Power BI Embedded
```

### Web Interface (2 panels, 1 page)
| Left Panel | Right Panel |
|---|---|
| Drag & drop file upload | Chat with Claude (natural language) |
| AI column mapping preview | "How much did I spend on dining in March?" |
| Confirm → data loaded | Claude calls agent_tools.py → queries DB |
| Power BI embedded dashboard | Replies with insights, auto-filters dashboard |

### Three AI Modes
1. **BUILD** (now): Claude Code in VS Code — writes schema, API, dbt models
2. **OPERATE** (future): Web chat box — Claude API + tool calling queries Supabase
3. **VISUALIZE** (future): Power BI embedded — real-time dashboards, no data skills needed

### agent_tools.py — The Bridge
Planned functions: `get_monthly_summary()`, `compare_months()`, `get_budget_status()`, `search_transactions()`, `explain_category_trend()`
Same pattern as Databricks agent: Python functions exposed as Claude API tools → call Supabase → return natural language.

## Cross-Platform Portability

The architecture is database-agnostic. The entire stack — API, dbt transforms, dashboards — runs on any major data platform by changing only the connection string.

| Layer | Supabase (current) | Snowflake | AWS | Azure |
|---|---|---|---|---|
| Database | PostgreSQL | Snowflake | Redshift / RDS / Aurora | SQL DB / Synapse |
| dbt adapter | `dbt-postgres` | `dbt-snowflake` | `dbt-redshift` | `dbt-fabric` / `dbt-sqlserver` |
| API | FastAPI (portable) | Same | Same (Lambda) | Same (App Service) |
| BI | Power BI | Power BI / Tableau | QuickSight / Power BI | Power BI |
| AI | Claude API | Same | Same (Bedrock) | Same (Azure OpenAI) |

**Why this works:** dbt models use `{{ ref() }}` and `{{ source() }}` — database-agnostic Jinja that compiles to the right SQL for each platform. All 5 models (`stg_transactions`, `fct_monthly_summary`, `fct_savings_rate`, `fct_budget_vs_actual`, `fct_expense_group_summary`) are identical across platforms. Only `profiles.yml` changes.

**Migration path:** Start on Supabase (free, simple). When customer data volume or compliance requires, migrate to Snowflake or AWS by swapping one config file. Zero model rewrites needed.

## Key Decisions

- **SCD Type 1** (overwrite). Why: personal tracker, no audit/history needs. How to apply: if multi-tenant SaaS phase begins, reconsider SCD2 for `categories` + `monthly_budgets`.
- **Hybrid schema** — fixed core columns + JSONB metadata for flexibility (planned for Phase 2 customer data).
- **Public repo** — for portfolio visibility. `.env` gitignored.
- **Supabase auth** — configured anon access for API operations. RLS policies set to public for single-user phase (tighten for multi-tenant).
- **Presentation language** — prefer "AI-paired implementation" / "Claude generated ~95% of the code" over "zero manual coding" (more credible and accurate).

## Progress to Date

### Done
- [x] Supabase account + project created
- [x] Schema + 22 seed categories applied
- [x] FastAPI backend (`api/main.py`) — full CRUD for transactions/categories/budgets/savings-goals
- [x] `.env` configured with correct Supabase URL + legacy anon key
- [x] API tested end-to-end (transaction created via `/docs`, verified in Supabase table editor)
- [x] dbt project scaffolded — 6 models running (2 staging views + 4 mart tables) with dim_date and fiscal period support
- [x] `seed_test_data.sql` — 3 months sample data (Feb/Mar/Apr 2026, ~60 rows)
- [x] Tools installed: GitHub CLI, Node.js 24.15.0, npm 11.12.1, Scoop, Supabase CLI, PowerShell 7, Starship
- [x] Git repo initialised, pushed to `xinxu-work/finflow-ai`
- [x] Commit author attribution fixed (force-push with noreply email)
- [x] Local branch renamed `master` → `main`, tracking `origin/main`
- [x] Project renamed to `expense_tracker` (under `Learning/AI_Practice/`)
- [x] AI Champion presentation prep — key takeaways, architecture narrative, 3-phase roadmap
- [x] `Expense_Tracker_Key_Takeaways.pdf` — 2-page PDF with web UI mockup, stack, architecture flow
- [x] Codex reviewed PDF — generated polished version with GPT Image-2 mockup + reportlab layout; 5 improvements applied to these notes
- [x] Databricks AI Agents + Microsoft Fabric background documented
- [x] Web UI product architecture designed (upload + chat + embedded dashboard)
- [x] `agent_tools.py` design — tool-calling bridge between Claude API and Supabase
- [x] Star Schema v2 — added `expense_groups` and `dim_date` dimension tables, UUID FKs replacing text joins
- [x] API updated — `/expense-groups`, `/group-budgets`, `savings_goal_id` on transactions
- [x] Star Schema v2 migration run on Supabase (2026-06-22) — `expense_groups` table created + 4 groups seeded, `categories` text FK→UUID FK, `monthly_group_budgets` text FK→UUID FK, `transactions` FK→`dim_date`, dbt views/tables dropped (recreated on next `dbt run`)
- [x] `verify_schema.py` updated for v2 schema + run successfully — all 7 checks passed (expense_groups, categories FK, monthly_budgets, group_budgets FK, savings_goals, transactions FK, constraints)
- [x] dbt walkthrough (2026-06-23) — profiles.yml explained, `{{ ref() }}` vs `{{ source() }}`, 6-model dependency chain understood, dbt adapters + deployment options mapped
- [x] Star Schema v3 designed (2026-06-23) — `types` replaces `expense_groups`, single `budgets` table replaces `monthly_budgets` + `monthly_group_budgets` (nullable `category_id` = envelope budget), `categories.type_id` replaces `type` VARCHAR + `expense_group_id` FK
- [x] SCD Type 2 added to budgets (2026-06-24) — `start_date` + `end_date` date-range versioning, old rows closed on update, only one active row per type/category (`end_date = '2030-01-01'`)
- [x] V3.1 bank import pipeline designed (2026-06-24) — `pay_dates` table (auto-detect salary dates), `merchant_rules` table (19 seed rules for auto-categorization), `v_pay_periods` view (dynamic periods from consecutive pay dates), `transactions.source/raw_description/import_batch_id` columns, `import_commbank.py` (5-step CSV pipeline), 7 new API endpoints
- [x] MS Foundry agent scaffolded (2026-06-24) — `foundry_agent.py` with 5 Supabase tool functions (get_monthly_spending, get_budget_status, get_monthly_summary, list_categories, search_transactions), Prompt Agents SDK pattern
- [x] Purchase affordability workflow implemented (2026-07-16) — deterministic `POST /advice/can-i-afford` service checks category or type-envelope budgets; Foundry tool handles questions such as “Can I buy $150 shoes this month?” and returns a correlated `activity_id`
- [x] March bank statement analysed + categorised (2026-06-29) — 156 CommBank transactions scanned, 75 expenses categorised against audited Living_Expense_Mar.xlsx, 15 unknowns resolved with user, ~$6,761 salary + ~$4,500 expenses mapped

### Pending
- [x] Map March living expenses (Google Sheet) to schema
- [x] Bulk insert real March/April data (26 transactions imported — 16 direct map + 10 from bank account breakdowns)
- [ ] Run v3+v3.1 migration on Supabase (`star_schema_v3_migration.sql`)
- [ ] Import 75 real March bank transactions into Supabase
- [ ] Auto-detect pay dates from salary deposits
- [ ] Install dbt-postgres + run dbt transformations (7 models)
- [ ] Build Power BI dashboard (3 pages: overview, budget, savings)
- [ ] Connect Supabase MCP to Claude Code
- [ ] Verify end-to-end: Supabase → dbt → Power BI → Foundry agent
- [ ] Future: onboard the Foundry agent to Agent 365 for enterprise identity, governance, monitoring, and lifecycle controls (not required for the personal prototype)
- [ ] Add GitHub topics/tags + enable Issues
- [ ] (Phase 2) AI CSV cleaner using Claude API
- [ ] (Phase 2) JSONB metadata column for flexible customer schema

## Issues Solved

- **Invalid API key** — new `sb_publishable_*` key didn't work; switched to legacy anon JWT.
- **DNS failure** — typo in Supabase URL (single `m` vs double `m`); fixed in `.env`.
- **500 from API** — RLS blocked anon; added public policies.
- **winget Supabase.CLI** — package missing; installed via Scoop bucket instead.
- **npm -g supabase** — Supabase blocks global npm install; Scoop is the supported path.
- **Commit author mismatch** — `xuxinxyz@gmail.com` linked to a different GitHub account; rewrote commit with `xinxu-work` noreply email.

## Mapping Helper (for March data)

When importing your March sheet, you'll need:
- `transaction_date` ← your date column
- `category_id` ← lookup by category name (I'll provide UUIDs)
- `amount` ← your amount column (positive number)
- `description` ← your notes column (optional)
- `payment_method` ← one of `card` / `cash` / `transfer` / `direct_debit` (defaults to `card`)
