-- Mart: Expense group (type) summary (v3 — SCD Type 2)
-- Compares actual spending vs budget at the type level
-- Filters to current (active) budgets only: end_date = '2030-01-01'

WITH transactions AS (
    SELECT * FROM {{ ref('stg_transactions') }}
),

categories AS (
    SELECT * FROM {{ ref('stg_categories') }}
),

-- Actual spending by type per month
actuals AS (
    SELECT
        t.fiscal_month,
        c.type_name AS expense_group,
        COUNT(*) AS transaction_count,
        SUM(t.amount) AS total_actual
    FROM transactions t
    JOIN categories c ON t.category_id = c.category_id
    WHERE c.type_name IN ('fixed', 'variable')
    GROUP BY t.fiscal_month, c.type_name
),

-- Current budgets from the unified budgets table
-- Both per-category (fixed) and envelope (variable), merged via SUM
budgets AS (
    SELECT
        t.name AS expense_group,
        SUM(b.budget_amount) AS total_budget
    FROM {{ source('expense_tracker', 'budgets') }} b
    JOIN {{ source('expense_tracker', 'types') }} t ON b.type_id = t.id
    WHERE t.name IN ('fixed', 'variable')
      AND b.end_date = '2030-01-01'     -- current (active) budgets only
    GROUP BY t.name
)

SELECT
    a.fiscal_month,
    a.expense_group,
    a.transaction_count,
    a.total_actual,
    b.total_budget,
    a.total_actual - b.total_budget AS over_under,
    CASE
        WHEN b.total_budget > 0
        THEN ROUND((a.total_actual / b.total_budget) * 100, 1)
        ELSE 0
    END AS utilisation_pct,
    CASE
        WHEN a.total_actual > b.total_budget THEN 'over'
        WHEN a.total_actual > b.total_budget * 0.9 THEN 'near_limit'
        ELSE 'on_track'
    END AS budget_status
FROM actuals a
LEFT JOIN budgets b
    ON a.expense_group = b.expense_group
ORDER BY a.fiscal_month DESC, a.expense_group
