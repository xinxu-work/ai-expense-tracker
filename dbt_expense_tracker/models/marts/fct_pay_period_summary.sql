-- Mart: Pay Period Summary
-- Default mode follows confirmed salary dates from v_pay_periods.
-- Calendar mode can be selected with: --vars '{period_mode: calendar}'
-- Transactions outside configured pay periods fall back to calendar months.

{% set selected_period_mode = var('period_mode', 'payday') %}

{% if selected_period_mode not in ['payday', 'calendar'] %}
    {{ exceptions.raise_compiler_error(
        "period_mode must be 'payday' or 'calendar', got: " ~ selected_period_mode
    ) }}
{% endif %}

WITH transactions AS (
    SELECT * FROM {{ ref('stg_transactions') }}
),

categories AS (
    SELECT * FROM {{ ref('stg_categories') }}
),

-- Assign every transaction to the selected reporting period.
periodised AS (
    SELECT
        {% if selected_period_mode == 'calendar' %}
        t.year_month AS period_label,
        DATE_TRUNC('month', t.transaction_date)::DATE AS period_start_date,
        (
            DATE_TRUNC('month', t.transaction_date)
            + INTERVAL '1 month'
            - INTERVAL '1 day'
        )::DATE AS period_end_date,
        'calendar' AS period_basis,
        {% else %}
        COALESCE(t.pay_period_start::TEXT, t.year_month) AS period_label,
        COALESCE(
            t.pay_period_start,
            DATE_TRUNC('month', t.transaction_date)::DATE
        ) AS period_start_date,
        COALESCE(
            t.pay_period_end,
            (
                DATE_TRUNC('month', t.transaction_date)
                + INTERVAL '1 month'
                - INTERVAL '1 day'
            )::DATE
        ) AS period_end_date,
        CASE
            WHEN t.pay_period_start IS NOT NULL THEN 'payday'
            ELSE 'calendar_fallback'
        END AS period_basis,
        {% endif %}
        t.category_id,
        t.amount,
        t.payment_method,
        t.source,
        t.calendar_year,
        t.calendar_month
    FROM transactions t
),

period_agg AS (
    SELECT
        period_label,
        period_start_date,
        period_end_date,
        period_basis,
        category_id,
        COUNT(*) AS transaction_count,
        SUM(amount) AS total_amount,
        AVG(amount) AS avg_amount
    FROM periodised
    GROUP BY
        period_label,
        period_start_date,
        period_end_date,
        period_basis,
        category_id
)

SELECT
    p.period_label,
    p.period_start_date,
    p.period_end_date,
    p.period_basis,
    p.category_id,
    c.category_name,
    c.category_type,
    c.type_name,
    p.transaction_count,
    p.total_amount,
    p.avg_amount,

    -- Running total per broad category type across reporting periods.
    SUM(p.total_amount) OVER (
        PARTITION BY c.category_type
        ORDER BY p.period_start_date
    ) AS running_total

FROM period_agg p
JOIN categories c ON p.category_id = c.category_id
ORDER BY p.period_start_date DESC, c.category_type, p.total_amount DESC
