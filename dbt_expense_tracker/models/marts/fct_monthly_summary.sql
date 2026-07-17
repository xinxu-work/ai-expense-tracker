-- Mart: Monthly summary by category
-- Key metrics for dashboard consumption

WITH transactions AS (
    SELECT * FROM {{ ref('stg_transactions') }}
),

categories AS (
    SELECT * FROM {{ ref('stg_categories') }}
),

monthly_agg AS (
    SELECT
        t.fiscal_month,
        t.calendar_year,
        t.calendar_month,
        t.category_id,
        c.category_name,
        c.category_type,
        COUNT(*) AS transaction_count,
        SUM(t.amount) AS total_amount,
        AVG(t.amount) AS avg_amount,
        MIN(t.amount) AS min_amount,
        MAX(t.amount) AS max_amount
    FROM transactions t
    JOIN categories c ON t.category_id = c.category_id
    GROUP BY
        t.fiscal_month,
        t.calendar_year,
        t.calendar_month,
        t.category_id,
        c.category_name,
        c.category_type
)

SELECT
    fiscal_month,
    calendar_year,
    calendar_month,
    category_id,
    category_name,
    category_type,
    transaction_count,
    total_amount,
    avg_amount,
    min_amount,
    max_amount,
    -- Running total within the year
    SUM(total_amount) OVER (
        PARTITION BY calendar_year, category_type
        ORDER BY fiscal_month
    ) AS ytd_amount
FROM monthly_agg
ORDER BY fiscal_month DESC, category_type, total_amount DESC
