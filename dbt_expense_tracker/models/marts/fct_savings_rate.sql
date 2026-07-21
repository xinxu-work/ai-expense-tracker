-- Savings-rate calculation by selected reporting period.
-- The default reporting period follows confirmed salary dates.

WITH period_summary AS (
    SELECT * FROM {{ ref('fct_pay_period_summary') }}
),

period_totals AS (
    SELECT
        period_label,
        period_start_date,
        period_end_date,
        period_basis,

        SUM(
            CASE
                WHEN category_type = 'income' THEN total_amount
                ELSE 0
            END
        ) AS total_income,

        SUM(
            CASE
                WHEN category_type = 'expense' THEN total_amount
                ELSE 0
            END
        ) AS total_expenses,

        SUM(
            CASE
                WHEN category_type = 'saving' THEN total_amount
                ELSE 0
            END
        ) AS total_savings

    FROM period_summary
    GROUP BY
        period_label,
        period_start_date,
        period_end_date,
        period_basis
)

SELECT
    period_label,
    period_start_date,
    period_end_date,
    period_basis,
    total_income,
    total_expenses,
    total_savings,
    total_income - total_expenses AS net_income,
    total_income - total_expenses - total_savings
        AS remaining_after_savings,

    CASE
        WHEN total_income > 0
        THEN ROUND(
            ((total_income - total_expenses) / total_income) * 100,
            1
        )
        ELSE 0
    END AS net_savings_rate_pct,

    CASE
        WHEN total_income > 0
        THEN ROUND((total_savings / total_income) * 100, 1)
        ELSE 0
    END AS explicit_savings_rate_pct,

    AVG(total_expenses) OVER (
        ORDER BY period_start_date
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS avg_expenses_3_periods,

    AVG(total_income) OVER (
        ORDER BY period_start_date
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS avg_income_3_periods

FROM period_totals
ORDER BY period_start_date DESC