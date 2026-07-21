-- Staging model: clean and type-cast raw transactions
-- Joins dim_date for calendar attributes + v_pay_periods for dynamic pay periods

WITH source AS (
    SELECT
        id,
        transaction_date,
        category_id,
        savings_goal_id,
        amount,
        description,
        payment_method,
        is_recurring,
        source,
        raw_description,
        import_batch_id,
        created_at,
        updated_at
    FROM {{ source('expense_tracker', 'transactions') }}
),

date_dim AS (
    SELECT * FROM {{ source('expense_tracker', 'dim_date') }}
),

-- Dynamic pay periods from detected salary dates
pay_periods AS (
    SELECT * FROM {{ source('expense_tracker', 'v_pay_periods') }}
)

SELECT
    t.id,
    t.transaction_date,
    t.category_id,
    t.savings_goal_id,
    t.amount,
    COALESCE(t.description, 'No description') AS description,
    t.payment_method,
    t.is_recurring,

    -- Bank import traceability
    t.source,
    t.raw_description,
    t.import_batch_id,

    -- From dim_date: calendar attributes
    d.year AS calendar_year,
    d.month AS calendar_month,
    d.day AS calendar_day,
    d.day_of_week,
    d.day_name,
    d.month_name,
    d.is_weekend,
    d.quarter,

    -- From dim_date: fiscal period (mid-month to mid-month) — LEGACY
    -- d.fiscal_year,
    -- d.fiscal_month AS fiscal_month_number,
    -- d.fiscal_month_label AS fiscal_month,
    -- d.first_of_fiscal_month,

    -- From v_pay_periods: dynamic pay period (auto-detected from salary dates)
    pp.period_start AS pay_period_start,
    pp.period_end AS pay_period_end,

    -- Convenience: YYYY-MM string for calendar-month grouping
    TO_CHAR(t.transaction_date, 'YYYY-MM') AS year_month,

    t.created_at,
    t.updated_at
FROM source t
JOIN date_dim d ON t.transaction_date = d.date
LEFT JOIN pay_periods pp
    ON t.transaction_date >= pp.period_start
    AND t.transaction_date <= pp.period_end

