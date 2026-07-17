-- Mart: Budget vs Actual comparison (v3 — SCD Type 2)
-- Sources from unified budgets table — current per-category budgets only

WITH budgets AS (
    SELECT
        id,
        type_id,
        category_id,
        start_date,
        budget_amount
    FROM {{ source('expense_tracker', 'budgets') }}
    WHERE category_id IS NOT NULL     -- per-category budgets only
      AND end_date = '2030-01-01'     -- current (active) budgets only
),

transactions AS (
    SELECT * FROM {{ ref('stg_transactions') }}
),

categories AS (
    SELECT * FROM {{ ref('stg_categories') }}
),

actual_spend AS (
    SELECT
        category_id,
        fiscal_month,
        SUM(amount) AS actual_amount,
        COUNT(*) AS transaction_count
    FROM transactions
    GROUP BY category_id, fiscal_month
)

SELECT
    a.fiscal_month,
    c.category_name,
    c.category_type,
    b.budget_amount,
    COALESCE(a.actual_amount, 0) AS actual_amount,
    b.budget_amount - COALESCE(a.actual_amount, 0) AS variance,
    CASE
        WHEN b.budget_amount > 0
        THEN ROUND((COALESCE(a.actual_amount, 0) / b.budget_amount) * 100, 1)
        ELSE 0
    END AS utilisation_pct,
    COALESCE(a.transaction_count, 0) AS transaction_count,
    b.start_date AS budget_since,
    CASE
        WHEN COALESCE(a.actual_amount, 0) > b.budget_amount THEN 'over_budget'
        WHEN COALESCE(a.actual_amount, 0) > b.budget_amount * 0.9 THEN 'near_budget'
        ELSE 'within_budget'
    END AS budget_status
FROM budgets b
JOIN categories c ON b.category_id = c.category_id
LEFT JOIN actual_spend a
    ON b.category_id = a.category_id
    AND a.fiscal_month >= TO_CHAR(b.start_date, 'YYYY-MM')
ORDER BY a.fiscal_month DESC, c.category_name
