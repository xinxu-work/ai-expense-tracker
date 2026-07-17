-- Mart: Pay Period Summary (dynamic, based on actual salary dates)
-- Groups spending by auto-detected pay periods instead of calendar months
-- Falls back to fiscal_month when pay_period_start is NULL (no pay_dates yet)

WITH transactions AS (
    SELECT * FROM {{ ref('stg_transactions') }}
),

categories AS (
    SELECT * FROM {{ ref('stg_categories') }}
),

-- Assign each transaction to a pay period or fallback to fiscal month
periodised AS (
    SELECT
        COALESCE(t.pay_period_start::TEXT, t.fiscal_month) AS period_label,
        COALESCE(t.pay_period_start, t.first_of_fiscal_month) AS period_start_date,
        t.category_id,
        t.amount,
        t.payment_method,
        t.source,
        t.calendar_year,
        t.calendar_month
    FROM transactions t
),

-- Aggregate by period + category
period_agg AS (
    SELECT
        period_label,
        period_start_date,
        category_id,
        COUNT(*) AS transaction_count,
        SUM(amount) AS total_amount,
        AVG(amount) AS avg_amount
    FROM periodised
    GROUP BY period_label, period_start_date, category_id
)

SELECT
    p.period_label,
    p.period_start_date,
    p.category_id,
    c.category_name,
    c.category_type,
    c.type_name,
    p.transaction_count,
    p.total_amount,
    p.avg_amount,

    -- Running total of spending per type within all recorded periods
    SUM(p.total_amount) OVER (
        PARTITION BY c.category_type
        ORDER BY p.period_start_date
    ) AS running_total

FROM period_agg p
JOIN categories c ON p.category_id = c.category_id
ORDER BY p.period_start_date DESC, c.category_type, p.total_amount DESC
