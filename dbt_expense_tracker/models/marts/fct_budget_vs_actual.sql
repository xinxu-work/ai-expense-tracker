-- Mart: category budget versus actual by selected reporting period.
-- The fiscal_month alias is retained for existing Power BI compatibility, but
-- its value is now the payday or calendar period label selected by dbt.

WITH budgets AS (
    SELECT
        id,
        type_id,
        category_id,
        start_date,
        end_date,
        budget_amount
    FROM {{ source('expense_tracker', 'budgets') }}
    WHERE category_id IS NOT NULL
      AND end_date = '2030-01-01'
),

categories AS (
    SELECT * FROM {{ ref('stg_categories') }}
),

period_actuals AS (
    SELECT
        category_id,
        period_label,
        period_start_date,
        period_end_date,
        period_basis,
        SUM(total_amount) AS actual_amount,
        SUM(transaction_count) AS transaction_count
    FROM {{ ref('fct_pay_period_summary') }}
    GROUP BY
        category_id,
        period_label,
        period_start_date,
        period_end_date,
        period_basis
),

periods AS (
    SELECT DISTINCT
        period_label,
        period_start_date,
        period_end_date,
        period_basis
    FROM period_actuals
)

SELECT
    p.period_label AS fiscal_month,
    p.period_start_date,
    p.period_end_date,
    p.period_basis,
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
        WHEN COALESCE(a.actual_amount, 0) >= b.budget_amount * 0.9 THEN 'near_budget'
        ELSE 'within_budget'
    END AS budget_status
FROM budgets b
JOIN categories c ON c.category_id = b.category_id
JOIN periods p
    ON p.period_end_date >= b.start_date
   AND p.period_start_date < b.end_date
LEFT JOIN period_actuals a
    ON a.category_id = b.category_id
   AND a.period_start_date = p.period_start_date
   AND a.period_end_date = p.period_end_date
ORDER BY p.period_start_date DESC, c.category_name
