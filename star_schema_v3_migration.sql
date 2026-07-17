-- Star Schema v3: Simplify budget model — single types + budgets tables
-- Replaces expense_groups, monthly_budgets, monthly_group_budgets
-- Run in your project's Supabase SQL Editor.

-- ============================================
-- 0. DROP dependent dbt objects so old columns/tables can be removed
--    staging = views, marts = tables
-- ============================================
DROP VIEW IF EXISTS public_staging.stg_categories CASCADE;
DROP VIEW IF EXISTS public_staging.stg_transactions CASCADE;
DROP TABLE IF EXISTS public_marts.fct_monthly_summary CASCADE;
DROP TABLE IF EXISTS public_marts.fct_savings_rate CASCADE;
DROP TABLE IF EXISTS public_marts.fct_budget_vs_actual CASCADE;
DROP TABLE IF EXISTS public_marts.fct_expense_group_summary CASCADE;
DROP VIEW IF EXISTS v_monthly_summary CASCADE;
DROP VIEW IF EXISTS v_budget_vs_actual CASCADE;

-- ============================================
-- 1. CREATE types table (replaces expense_groups)
-- ============================================
CREATE TABLE IF NOT EXISTS types (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name       VARCHAR(20) NOT NULL UNIQUE,
    sort_order INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO types (name, sort_order) VALUES
    ('fixed',    1),
    ('variable', 2),
    ('income',   3),
    ('saving',   4)
ON CONFLICT (name) DO NOTHING;

-- ============================================
-- 2. MIGRATE categories: type VARCHAR + expense_group_id FK → type_id FK
-- ============================================

-- Add new type_id column
ALTER TABLE categories ADD COLUMN IF NOT EXISTS type_id UUID;

-- Populate type_id by matching old expense_group name to types.name
-- expense_groups.name = types.name exactly (fixed, variable, income, saving)
UPDATE categories c
SET type_id = t.id
FROM expense_groups eg, types t
WHERE c.expense_group_id = eg.id
  AND eg.name = t.name;

-- Verify all categories mapped
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM categories WHERE type_id IS NULL) THEN
        RAISE EXCEPTION 'Some categories have NULL type_id — check mapping';
    END IF;
END $$;

ALTER TABLE categories ALTER COLUMN type_id SET NOT NULL;

ALTER TABLE categories
ADD CONSTRAINT fk_categories_type
FOREIGN KEY (type_id) REFERENCES types(id);

-- Drop old columns
ALTER TABLE categories DROP COLUMN IF EXISTS type;               -- VARCHAR CHECK (v1)
ALTER TABLE categories DROP COLUMN IF EXISTS expense_group_id;   -- UUID FK (v2)
ALTER TABLE categories DROP COLUMN IF EXISTS expense_group;      -- legacy text (v1, if exists)

-- ============================================
-- 2b. ADD bank import columns to transactions
--     source: 'manual' (hand-entered) vs 'bank_import' (CSV)
--     raw_description: original bank text before categorization
--     import_batch_id: groups rows from the same CSV import
-- ============================================
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'manual';
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS raw_description VARCHAR(255);
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS import_batch_id VARCHAR(50);

-- ============================================
-- 3. CREATE budgets table (replaces monthly_budgets + monthly_group_budgets)
--    SCD Type 2: date-range versioning with start_date + end_date
--    category_id IS NOT NULL → per-category budget (fixed expenses)
--    category_id IS NULL     → envelope budget for the type (variable expenses)
--    Default end_date = '2030-01-01' = "currently active"
-- ============================================
CREATE TABLE IF NOT EXISTS budgets (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type_id       UUID NOT NULL REFERENCES types(id),
    category_id   UUID REFERENCES categories(id),   -- NULLABLE: NULL = envelope budget for the type
    start_date    DATE NOT NULL,
    end_date      DATE NOT NULL DEFAULT '2030-01-01',
    budget_amount DECIMAL(10, 2) NOT NULL CHECK (budget_amount >= 0),
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Partial unique indexes: only ONE active row (end_date = '2030-01-01') per mode
-- Historical rows (end_date < '2030-01-01') can coexist freely
CREATE UNIQUE INDEX IF NOT EXISTS idx_budgets_active_category
ON budgets(type_id, category_id)
WHERE category_id IS NOT NULL AND end_date = '2030-01-01';

CREATE UNIQUE INDEX IF NOT EXISTS idx_budgets_active_envelope
ON budgets(type_id)
WHERE category_id IS NULL AND end_date = '2030-01-01';

-- ============================================
-- 3b. CREATE merchant_rules — keyword → category mapping for auto-categorization
-- ============================================
CREATE TABLE IF NOT EXISTS merchant_rules (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    keyword     VARCHAR(100) NOT NULL UNIQUE,
    category_id UUID NOT NULL REFERENCES categories(id),
    priority    INT DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Seed initial rules
INSERT INTO merchant_rules (keyword, category_id, priority) VALUES
    ('WOOLWORTHS',  (SELECT id FROM categories WHERE name = 'Groceries'),      10),
    ('COLES',       (SELECT id FROM categories WHERE name = 'Groceries'),      10),
    ('ALDI',        (SELECT id FROM categories WHERE name = 'Groceries'),      10),
    ('OPTUS',       (SELECT id FROM categories WHERE name = 'Phone & Internet'), 5),
    ('TELSTRA',     (SELECT id FROM categories WHERE name = 'Phone & Internet'), 5),
    ('NETFLIX',     (SELECT id FROM categories WHERE name = 'Subscriptions'),  5),
    ('SPOTIFY',     (SELECT id FROM categories WHERE name = 'Subscriptions'),  5),
    ('UBER',        (SELECT id FROM categories WHERE name = 'Transport'),       5),
    ('OPAL',        (SELECT id FROM categories WHERE name = 'Transport'),       5),
    ('LINKT',       (SELECT id FROM categories WHERE name = 'Transport'),       5),
    ('AMAZON',      (SELECT id FROM categories WHERE name = 'Shopping'),        3),
    ('KMART',       (SELECT id FROM categories WHERE name = 'Shopping'),        3),
    ('BUNNINGS',    (SELECT id FROM categories WHERE name = 'Shopping'),        3),
    ('CHEMIST',     (SELECT id FROM categories WHERE name = 'Health'),          3),
    ('MEDICARE',    (SELECT id FROM categories WHERE name = 'Health'),          3),
    ('GYM',         (SELECT id FROM categories WHERE name = 'Health'),          3),
    ('ENERGY',      (SELECT id FROM categories WHERE name = 'Utilities'),      5),
    ('AGL',         (SELECT id FROM categories WHERE name = 'Utilities'),      5),
    ('ORIGIN',      (SELECT id FROM categories WHERE name = 'Utilities'),      5)
ON CONFLICT (keyword) DO NOTHING;

-- ============================================
-- 3c. CREATE pay_dates — auto-detected salary dates for dynamic pay periods
-- ============================================
CREATE TABLE IF NOT EXISTS pay_dates (
    pay_date    DATE PRIMARY KEY,
    source      VARCHAR(20) DEFAULT 'auto',
    note        VARCHAR(100)
);

-- ============================================
-- 4. MIGRATE monthly_budgets data → budgets (per-category)
--    year_month → start_date, end_date = '2030-01-01' (active)
-- ============================================
INSERT INTO budgets (type_id, category_id, start_date, end_date, budget_amount)
SELECT c.type_id, mb.category_id, mb.year_month, '2030-01-01', mb.budget_amount
FROM monthly_budgets mb
JOIN categories c ON mb.category_id = c.id
ON CONFLICT (type_id, category_id) WHERE category_id IS NOT NULL AND end_date = '2030-01-01'
DO UPDATE SET budget_amount = EXCLUDED.budget_amount;

-- ============================================
-- 5. MIGRATE monthly_group_budgets data → budgets (envelope)
--    year_month → start_date, end_date = '2030-01-01' (active)
-- ============================================
INSERT INTO budgets (type_id, category_id, start_date, end_date, budget_amount)
SELECT t.id, NULL, mgb.year_month, '2030-01-01', mgb.budget_amount
FROM monthly_group_budgets mgb
JOIN expense_groups eg ON mgb.expense_group_id = eg.id
JOIN types t ON eg.name = t.name
ON CONFLICT (type_id) WHERE category_id IS NULL AND end_date = '2030-01-01'
DO UPDATE SET budget_amount = EXCLUDED.budget_amount;

-- ============================================
-- 6. DROP obsolete tables
-- ============================================
DROP TABLE IF EXISTS monthly_group_budgets CASCADE;
DROP TABLE IF EXISTS monthly_budgets CASCADE;
DROP TABLE IF EXISTS expense_groups CASCADE;

-- ============================================
-- 7. RLS + policies for new tables
-- ============================================
ALTER TABLE types ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public all" ON types;
CREATE POLICY "Allow public all" ON types
    FOR ALL TO anon USING (true) WITH CHECK (true);

ALTER TABLE budgets ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public all" ON budgets;
CREATE POLICY "Allow public all" ON budgets
    FOR ALL TO anon USING (true) WITH CHECK (true);

ALTER TABLE merchant_rules ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public all" ON merchant_rules;
CREATE POLICY "Allow public all" ON merchant_rules
    FOR ALL TO anon USING (true) WITH CHECK (true);

ALTER TABLE pay_dates ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public all" ON pay_dates;
CREATE POLICY "Allow public all" ON pay_dates
    FOR ALL TO anon USING (true) WITH CHECK (true);

-- ============================================
-- 8. RECREATE legacy views + v_pay_periods
-- ============================================
CREATE OR REPLACE VIEW v_monthly_summary AS
SELECT
    DATE_TRUNC('month', t.transaction_date)::DATE AS month,
    ts.name AS type_name,
    c.name AS category_name,
    COUNT(*) AS transaction_count,
    SUM(t.amount) AS total_amount,
    AVG(t.amount) AS avg_amount
FROM transactions t
JOIN categories c ON t.category_id = c.id
JOIN types ts ON c.type_id = ts.id
GROUP BY DATE_TRUNC('month', t.transaction_date), ts.name, c.name
ORDER BY month DESC, ts.name, total_amount DESC;

CREATE OR REPLACE VIEW v_budget_vs_actual AS
SELECT
    DATE_TRUNC('month', t.transaction_date)::DATE AS month,
    c.name AS category_name,
    b.budget_amount,
    COALESCE(SUM(t.amount), 0) AS actual_amount,
    b.budget_amount - COALESCE(SUM(t.amount), 0) AS remaining,
    CASE
        WHEN b.budget_amount > 0
        THEN ROUND((COALESCE(SUM(t.amount), 0) / b.budget_amount) * 100, 1)
        ELSE 0
    END AS utilisation_pct
FROM budgets b
JOIN categories c ON b.category_id = c.id
LEFT JOIN transactions t
    ON t.category_id = b.category_id
    AND t.transaction_date >= b.start_date
WHERE b.category_id IS NOT NULL
  AND b.end_date = '2030-01-01'  -- current budgets only
GROUP BY DATE_TRUNC('month', t.transaction_date), c.name, b.budget_amount
ORDER BY month DESC, c.name;

-- v_pay_periods: dynamic pay periods derived from consecutive pay_dates
CREATE OR REPLACE VIEW v_pay_periods AS
SELECT
    pay_date AS period_start,
    COALESCE(
        LEAD(pay_date) OVER (ORDER BY pay_date) - INTERVAL '1 day',
        '2030-01-01'::DATE
    ) AS period_end
FROM pay_dates
ORDER BY pay_date;

-- ============================================
-- 9. VERIFY
-- ============================================
SELECT 'types' AS tbl, COUNT(*) AS rows FROM types
UNION ALL
SELECT 'budgets_total', COUNT(*) FROM budgets
UNION ALL
SELECT 'budgets_per_category', COUNT(*) FROM budgets WHERE category_id IS NOT NULL
UNION ALL
SELECT 'budgets_envelope', COUNT(*) FROM budgets WHERE category_id IS NULL
UNION ALL
SELECT 'categories_migrated', COUNT(*) FROM categories WHERE type_id IS NOT NULL
UNION ALL
SELECT 'merchant_rules', COUNT(*) FROM merchant_rules
UNION ALL
SELECT 'pay_dates', COUNT(*) FROM pay_dates
UNION ALL
SELECT 'FK_constraints', COUNT(*) FROM information_schema.table_constraints
    WHERE table_schema = 'public' AND constraint_type = 'FOREIGN KEY';

-- Show types table
SELECT * FROM types ORDER BY sort_order;

-- Show category → type mapping (sample)
SELECT c.name AS category, t.name AS type, t.sort_order
FROM categories c
JOIN types t ON c.type_id = t.id
ORDER BY t.sort_order, c.name;

-- Show budgets with type + category context
SELECT
    ts.name AS type_name,
    CASE WHEN b.category_id IS NOT NULL THEN c.name ELSE '— ALL —' END AS category_name,
    b.start_date,
    b.end_date,
    b.budget_amount,
    CASE WHEN b.end_date = '2030-01-01' THEN 'active' ELSE 'historical' END AS status
FROM budgets b
JOIN types ts ON b.type_id = ts.id
LEFT JOIN categories c ON b.category_id = c.id
ORDER BY ts.sort_order, b.category_id NULLS LAST, b.start_date;
