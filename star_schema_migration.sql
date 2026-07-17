-- Star Schema Migration
-- Adds dim_date, savings_goal_id FK to transactions
-- Run this in Supabase SQL Editor:
-- Run in your project's Supabase SQL Editor.

-- ============================================
-- 1. CREATE dim_date (Date Dimension)
-- ============================================
CREATE TABLE IF NOT EXISTS dim_date (
    date DATE PRIMARY KEY,
    year INT NOT NULL,
    month INT NOT NULL,
    day INT NOT NULL,
    day_of_week INT NOT NULL,           -- 0=Sun, 6=Sat
    day_name VARCHAR(10) NOT NULL,       -- Monday, Tuesday...
    month_name VARCHAR(10) NOT NULL,     -- January, February...
    is_weekend BOOLEAN NOT NULL,
    quarter INT NOT NULL,                -- 1, 2, 3, 4
    -- Fiscal period: if day >= 15, same month; if day < 15, previous month
    fiscal_year INT NOT NULL,
    fiscal_month INT NOT NULL,
    fiscal_month_label VARCHAR(7) NOT NULL,  -- '2026-03'
    first_of_calendar_month DATE NOT NULL,   -- '2026-03-01'
    first_of_fiscal_month DATE NOT NULL      -- '2026-03-15'
);

-- Populate dim_date with 3 years of data (2025-01-01 to 2027-12-31)
INSERT INTO dim_date
SELECT
    dt AS date,
    EXTRACT(YEAR FROM dt)::INT AS year,
    EXTRACT(MONTH FROM dt)::INT AS month,
    EXTRACT(DAY FROM dt)::INT AS day,
    EXTRACT(DOW FROM dt)::INT AS day_of_week,
    TO_CHAR(dt, 'Day') AS day_name,
    TO_CHAR(dt, 'Month') AS month_name,
    EXTRACT(DOW FROM dt) IN (0, 6) AS is_weekend,
    EXTRACT(QUARTER FROM dt)::INT AS quarter,
    -- Fiscal period: shift back 13 days, then extract
    EXTRACT(YEAR FROM dt - INTERVAL '13 days')::INT AS fiscal_year,
    EXTRACT(MONTH FROM dt - INTERVAL '13 days')::INT AS fiscal_month,
    TO_CHAR(dt - INTERVAL '13 days', 'YYYY-MM') AS fiscal_month_label,
    DATE_TRUNC('month', dt)::DATE AS first_of_calendar_month,
    -- First of fiscal month: the 15th-ish day
    (DATE_TRUNC('month', dt - INTERVAL '13 days') + INTERVAL '13 days')::DATE AS first_of_fiscal_month
FROM generate_series('2025-01-01'::DATE, '2027-12-31'::DATE, '1 day'::INTERVAL) AS dt
ON CONFLICT (date) DO NOTHING;

-- ============================================
-- 2. ADD savings_goal_id FK to transactions
-- ============================================
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS savings_goal_id UUID
    REFERENCES savings_goals(id);

-- ============================================
-- 3. ENABLE RLS on dim_date
-- ============================================
ALTER TABLE dim_date ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public read" ON dim_date
    FOR SELECT TO anon USING (true);

-- ============================================
-- 4. VERIFY
-- ============================================
SELECT 'dim_date' AS object, COUNT(*) AS rows FROM dim_date
UNION ALL
SELECT 'transactions columns', COUNT(*) FROM information_schema.columns
    WHERE table_name = 'transactions';

-- Show dim_date sample
SELECT * FROM dim_date WHERE date BETWEEN '2026-03-14' AND '2026-04-14'
ORDER BY date
LIMIT 10;
