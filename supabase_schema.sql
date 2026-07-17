-- ============================================================
-- Expense Tracker — Supabase Schema (Star Schema v3)
-- Database: PostgreSQL (Supabase)
-- Timezone: Australia/Sydney (AEST/AEDT)
-- Fiscal period: 14th to 13th (salary paid mid-month)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- SHARED TRIGGER: auto-update updated_at on any table
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 1. DIM_DATE  (date dimension — star schema anchor)
--    Covers 2025-01-01 to 2027-12-31 (1095 rows)
--    Fiscal month: day >= 14 → same month, day < 14 → previous month
-- ============================================================
CREATE TABLE dim_date (
    date                    DATE PRIMARY KEY,
    year                    INT NOT NULL,
    month                   INT NOT NULL,
    day                     INT NOT NULL,
    day_of_week             INT NOT NULL,           -- 0=Sun, 6=Sat
    day_name                VARCHAR(10) NOT NULL,
    month_name              VARCHAR(10) NOT NULL,
    is_weekend              BOOLEAN NOT NULL,
    quarter                 INT NOT NULL,
    fiscal_year             INT NOT NULL,
    fiscal_month            INT NOT NULL,
    fiscal_month_label      VARCHAR(7) NOT NULL,    -- 'YYYY-MM'
    first_of_calendar_month DATE NOT NULL,
    first_of_fiscal_month   DATE NOT NULL
);

INSERT INTO dim_date
SELECT
    dt AS date,
    EXTRACT(YEAR FROM dt)::INT,
    EXTRACT(MONTH FROM dt)::INT,
    EXTRACT(DAY FROM dt)::INT,
    EXTRACT(DOW FROM dt)::INT,
    TO_CHAR(dt, 'Day'),
    TO_CHAR(dt, 'Month'),
    EXTRACT(DOW FROM dt) IN (0, 6),
    EXTRACT(QUARTER FROM dt)::INT,
    EXTRACT(YEAR FROM dt - INTERVAL '13 days')::INT,
    EXTRACT(MONTH FROM dt - INTERVAL '13 days')::INT,
    TO_CHAR(dt - INTERVAL '13 days', 'YYYY-MM'),
    DATE_TRUNC('month', dt)::DATE,
    (DATE_TRUNC('month', dt - INTERVAL '13 days') + INTERVAL '13 days')::DATE
FROM generate_series('2025-01-01'::DATE, '2027-12-31'::DATE, '1 day'::INTERVAL) AS dt
ON CONFLICT (date) DO NOTHING;

-- ============================================================
-- 2. TYPES  (type dimension — replaces expense_groups)
--    4 rows: fixed, variable, income, saving
--    Fixed = per-category budgets, Variable = envelope budgets
-- ============================================================
CREATE TABLE types (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name       VARCHAR(20) NOT NULL UNIQUE,
    sort_order INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO types (name, sort_order) VALUES
    ('fixed',    1),   -- Rent, bills, subscriptions — budgeted per category
    ('variable', 2),   -- Food, transport, shopping — budgeted as an envelope
    ('income',   3),
    ('saving',   4);

-- ============================================================
-- 3. CATEGORIES  (category dimension)
--    type_id FK replaces v2 expense_group_id + type VARCHAR
-- ============================================================
CREATE TABLE categories (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name       VARCHAR(50) NOT NULL UNIQUE,
    type_id    UUID NOT NULL REFERENCES types(id),
    icon       VARCHAR(10),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed 22 default categories
INSERT INTO categories (name, type_id) VALUES
    -- Fixed expenses
    ('Rent',             (SELECT id FROM types WHERE name = 'fixed')),
    ('Utilities',        (SELECT id FROM types WHERE name = 'fixed')),
    ('Phone & Internet', (SELECT id FROM types WHERE name = 'fixed')),
    ('Insurance',        (SELECT id FROM types WHERE name = 'fixed')),
    ('Health',           (SELECT id FROM types WHERE name = 'fixed')),
    ('Subscriptions',    (SELECT id FROM types WHERE name = 'fixed')),
    -- Variable expenses
    ('Groceries',        (SELECT id FROM types WHERE name = 'variable')),
    ('Dining Out',       (SELECT id FROM types WHERE name = 'variable')),
    ('Transport',        (SELECT id FROM types WHERE name = 'variable')),
    ('Entertainment',    (SELECT id FROM types WHERE name = 'variable')),
    ('Shopping',         (SELECT id FROM types WHERE name = 'variable')),
    ('Personal Care',    (SELECT id FROM types WHERE name = 'variable')),
    ('Education',        (SELECT id FROM types WHERE name = 'variable')),
    ('Other Expense',    (SELECT id FROM types WHERE name = 'variable')),
    -- Income
    ('Salary',           (SELECT id FROM types WHERE name = 'income')),
    ('Freelance',        (SELECT id FROM types WHERE name = 'income')),
    ('Investment',       (SELECT id FROM types WHERE name = 'income')),
    ('Other Income',     (SELECT id FROM types WHERE name = 'income')),
    -- Saving
    ('Emergency Fund',      (SELECT id FROM types WHERE name = 'saving')),
    ('Investment Savings',  (SELECT id FROM types WHERE name = 'saving')),
    ('Travel Fund',         (SELECT id FROM types WHERE name = 'saving')),
    ('General Savings',     (SELECT id FROM types WHERE name = 'saving'));

-- ============================================================
-- 4. SAVINGS_GOALS  (dimension — savings targets)
-- ============================================================
CREATE TABLE savings_goals (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name           VARCHAR(100) NOT NULL,
    target_amount  DECIMAL(10, 2) NOT NULL CHECK (target_amount > 0),
    current_amount DECIMAL(10, 2) DEFAULT 0 CHECK (current_amount >= 0),
    target_date    DATE,
    status         VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'paused')),
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER trigger_savings_goals_updated
    BEFORE UPDATE ON savings_goals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- 5. TRANSACTIONS  (fact table — centre of the star)
--    FKs: dim_date, categories, savings_goals (nullable)
-- ============================================================
CREATE TABLE transactions (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_date DATE NOT NULL REFERENCES dim_date(date),
    category_id      UUID NOT NULL REFERENCES categories(id),
    savings_goal_id  UUID REFERENCES savings_goals(id),     -- nullable: only savings deposits
    amount           DECIMAL(10, 2) NOT NULL CHECK (amount > 0),
    description      VARCHAR(255),
    payment_method   VARCHAR(20) DEFAULT 'card'
                         CHECK (payment_method IN ('card', 'cash', 'transfer', 'direct_debit')),
    is_recurring     BOOLEAN DEFAULT FALSE,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_transactions_date     ON transactions(transaction_date);
CREATE INDEX idx_transactions_category ON transactions(category_id);
CREATE INDEX idx_transactions_goal     ON transactions(savings_goal_id) WHERE savings_goal_id IS NOT NULL;

CREATE TRIGGER trigger_transactions_updated
    BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Additional columns for bank import support
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'manual';
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS raw_description VARCHAR(255);
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS import_batch_id VARCHAR(50);

-- ============================================================
-- 6. BUDGETS  (single budget table — SCD Type 2 date-range versioning)
--    category_id IS NOT NULL → per-category budget (fixed expenses)
--    category_id IS NULL     → envelope budget for the type (variable expenses)
--    end_date = '2030-01-01' → currently active budget (DEFAULT)
--    end_date < '2030-01-01' → historical record (closed on update)
-- ============================================================
CREATE TABLE budgets (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type_id       UUID NOT NULL REFERENCES types(id),
    category_id   UUID REFERENCES categories(id),   -- NULLABLE: NULL = envelope for the type
    start_date    DATE NOT NULL,
    end_date      DATE NOT NULL DEFAULT '2030-01-01',
    budget_amount DECIMAL(10, 2) NOT NULL CHECK (budget_amount >= 0),
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Partial unique indexes: only ONE active row (end_date = '2030-01-01') per mode
-- Historical rows (end_date < '2030-01-01') can coexist freely
CREATE UNIQUE INDEX idx_budgets_active_category
ON budgets(type_id, category_id)
WHERE category_id IS NOT NULL AND end_date = '2030-01-01';

CREATE UNIQUE INDEX idx_budgets_active_envelope
ON budgets(type_id)
WHERE category_id IS NULL AND end_date = '2030-01-01';

-- ============================================================
-- 6b. MERCHANT_RULES — keyword → category mapping for auto-categorization
-- ============================================================
CREATE TABLE merchant_rules (
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

-- ============================================================
-- 6c. PAY_DATES — detected salary dates for dynamic pay periods
-- ============================================================
CREATE TABLE pay_dates (
    pay_date    DATE PRIMARY KEY,
    source      VARCHAR(20) DEFAULT 'auto',
    note        VARCHAR(100)
);

-- ============================================================
-- 7. ROW LEVEL SECURITY
-- ============================================================
ALTER TABLE dim_date       ENABLE ROW LEVEL SECURITY;
ALTER TABLE types          ENABLE ROW LEVEL SECURITY;
ALTER TABLE categories     ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE budgets        ENABLE ROW LEVEL SECURITY;
ALTER TABLE savings_goals  ENABLE ROW LEVEL SECURITY;

-- Public read on reference/dimension tables
CREATE POLICY "Allow public read" ON dim_date
    FOR SELECT TO anon USING (true);

CREATE POLICY "Allow public all" ON types
    FOR ALL TO anon USING (true) WITH CHECK (true);

CREATE POLICY "Allow public all" ON categories
    FOR ALL TO anon USING (true) WITH CHECK (true);

-- Full access on fact and planning tables (single-user; tighten for multi-tenant)
CREATE POLICY "Allow public all" ON transactions
    FOR ALL TO anon USING (true) WITH CHECK (true);

CREATE POLICY "Allow public all" ON budgets
    FOR ALL TO anon USING (true) WITH CHECK (true);

CREATE POLICY "Allow public all" ON merchant_rules
    FOR ALL TO anon USING (true) WITH CHECK (true);

CREATE POLICY "Allow public all" ON pay_dates
    FOR ALL TO anon USING (true) WITH CHECK (true);

CREATE POLICY "Allow public all" ON savings_goals
    FOR ALL TO anon USING (true) WITH CHECK (true);

-- ============================================================
-- 8. LEGACY VIEWS  (kept for backwards compatibility with API)
-- ============================================================
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

-- ============================================================
-- 9. V_PAY_PERIODS — dynamic pay period boundaries (VIEW)
--    Derived from consecutive pay_dates using LEAD window function
--    Example: 2026-03-13 → 2026-04-13, 2026-04-14 → 2026-05-13, ...
-- ============================================================
CREATE OR REPLACE VIEW v_pay_periods AS
SELECT
    pay_date AS period_start,
    COALESCE(
        LEAD(pay_date) OVER (ORDER BY pay_date) - INTERVAL '1 day',
        '2030-01-01'::DATE
    ) AS period_end
FROM pay_dates
ORDER BY pay_date;
