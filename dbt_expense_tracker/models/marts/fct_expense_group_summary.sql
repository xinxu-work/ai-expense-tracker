-- Mart: fixed and variable living expenses versus budget by reporting period.
-- The fiscal_month alias is retained for existing Power BI compatibility.

WITH period_summary AS (
    SELECT * FROM {{ ref('fct_pay_period_summary') }}
),

actuals AS (
    SELECT
        period_label,
        period_start_date,
        period_end_date,
        period_basis,
        type_name AS expense_group,
        SUM(transaction_count) AS transaction_count,
        SUM(total_amount) AS total_actual
    FROM period_summary
    WHERE type_name IN ('fixed', 'variable')
    GROUP BY
        period_label,
        period_start_date,
        period_end_date,
        period_basis,
        type_name
),

budgets AS (
    SELECT
        t.name AS expense_group,
        SUM(b.budget_amount) AS total_budget
    FROM {{ source('expense_tracker', 'budgets') }} b
    JOIN {{ source('expense_tracker', 'types') }} t ON t.id = b.type_id
    WHERE t.name IN ('fixed', 'variable')
      AND b.end_date = '2030-01-01'
    GROUP BY t.name
)

SELECT
    a.period_label AS fiscal_month,
    a.period_start_date,
    a.period_end_date,
    a.period_basis,
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
        WHEN a.total_actual >= b.total_budget * 0.9 THEN 'near_limit'
        ELSE 'on_track'
    END AS budget_status
FROM actuals a
LEFT JOIN budgets b ON b.expense_group = a.expense_group
ORDER BY a.period_start_date DESC, a.expense_group
