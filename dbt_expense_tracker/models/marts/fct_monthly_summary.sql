-- Reporting-period summary by category.
-- Uses confirmed payday periods by default.

WITH period_summary AS (
    SELECT * FROM {{ ref('fct_pay_period_summary') }}
)

SELECT
    period_label,
    period_start_date,
    period_end_date,
    period_basis,
    category_id,
    category_name,
    category_type,
    type_name,
    transaction_count,
    total_amount,
    avg_amount,

    SUM(total_amount) OVER (
        PARTITION BY category_type
        ORDER BY period_start_date
    ) AS running_total

FROM period_summary
ORDER BY period_start_date DESC, category_type, total_amount DESC