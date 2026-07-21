# dbt Expense Tracker Model Flow

dbt builds the models automatically in dependency order when you run `dbt run`; you do not run each SQL file manually. The staging model reads the existing Supabase tables and views, cleans and enriches the transaction data, and is materialized as a view. The mart models use the staging view and are materialized as reporting tables. dbt discovers this order from `{{ ref(...) }}` references, then `dbt test` validates the generated objects and their data.

```mermaid
flowchart TD
    T["public.transactions"] --> S["stg_transactions.sql\nStaging view"]
    D["public.dim_date\nCalendar attributes"] --> S
    P["public.v_pay_periods\nPayday boundaries"] --> S

    S --> PPS["fct_pay_period_summary.sql\nMart table"]

    PPS --> B["fct_budget_vs_actual.sql\nMart table"]
    PPS --> E["fct_expense_group_summary.sql\nMart table"]
    PPS --> M["fct_monthly_summary.sql\nMart table"]
    PPS --> R["fct_savings_rate.sql\nMart table"]

    RUN["dbt run"] -. "builds in dependency order" .-> S
    RUN -. "then builds downstream marts" .-> PPS
    TEST["dbt test"] -. "validates models" .-> B
    TEST -. "validates models" .-> R
```

Typical commands:

```powershell
dbt run
dbt test
```
