-- Star Schema v3.1: migrate the live V2 schema to unified types and budgets.
--
-- IMPORTANT
--   * This is a strict, one-time V2 -> V3.1 migration.
--   * Run the complete file in one Supabase SQL Editor execution.
--   * Do not rerun it after a successful COMMIT.
--   * Any error before COMMIT rolls back every schema and data change.

BEGIN;

SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '5min';

-- Prevent writes while the migration copies and validates V2 data.
LOCK TABLE
    public.categories,
    public.transactions,
    public.expense_groups,
    public.monthly_budgets,
    public.monthly_group_budgets
IN ACCESS EXCLUSIVE MODE;

-- ---------------------------------------------------------------------------
-- 0. PREFLIGHT: require the expected V2 shape and reject partial/rerun states.
-- ---------------------------------------------------------------------------
DO $preflight$
BEGIN
    IF to_regclass('public.expense_groups') IS NULL
       OR to_regclass('public.monthly_budgets') IS NULL
       OR to_regclass('public.monthly_group_budgets') IS NULL THEN
        RAISE EXCEPTION
            'V2 preflight failed: one or more legacy tables are missing';
    END IF;

    IF to_regclass('public.types') IS NOT NULL
       OR to_regclass('public.budgets') IS NOT NULL
       OR to_regclass('public.merchant_rules') IS NOT NULL
       OR to_regclass('public.pay_dates') IS NOT NULL
       OR to_regclass('public.v_pay_periods') IS NOT NULL THEN
        RAISE EXCEPTION
            'V3 preflight failed: V3 objects already exist; do not rerun this migration';
    END IF;

    IF (SELECT COUNT(*) FROM public.expense_groups) <> 4
       OR (SELECT COUNT(DISTINCT name) FROM public.expense_groups) <> 4
       OR EXISTS (
            SELECT 1
            FROM public.expense_groups
            WHERE name NOT IN ('fixed', 'variable', 'income', 'saving')
       ) THEN
        RAISE EXCEPTION
            'V2 preflight failed: expense_groups must contain fixed, variable, income, and saving';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM public.categories c
        LEFT JOIN public.expense_groups eg ON eg.id = c.expense_group_id
        WHERE c.expense_group_id IS NULL OR eg.id IS NULL
    ) THEN
        RAISE EXCEPTION
            'V2 preflight failed: one or more categories have no valid expense_group';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM public.categories c
        JOIN public.expense_groups eg ON eg.id = c.expense_group_id
        WHERE c.type IS DISTINCT FROM eg.type
    ) THEN
        RAISE EXCEPTION
            'V2 preflight failed: category.type does not match expense_group.type';
    END IF;

    IF (
        SELECT COUNT(*)
        FROM public.categories
        WHERE name IN (
            'Groceries', 'Phone & Internet', 'Subscriptions', 'Transport',
            'Shopping', 'Health', 'Utilities'
        )
    ) <> 7 THEN
        RAISE EXCEPTION
            'V2 preflight failed: a category required by merchant-rule seeds is missing';
    END IF;

    IF EXISTS (
        SELECT category_id
        FROM public.monthly_budgets
        GROUP BY category_id
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION
            'V2 preflight failed: multiple active monthly_budgets exist for a category';
    END IF;

    IF EXISTS (
        SELECT expense_group_id
        FROM public.monthly_group_budgets
        GROUP BY expense_group_id
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION
            'V2 preflight failed: multiple active monthly_group_budgets exist for a group';
    END IF;
END
$preflight$;

-- Drop only the known dbt objects. Avoid CASCADE so an unexpected dependency
-- stops and rolls back the migration instead of being silently removed.
DROP TABLE IF EXISTS public_marts.fct_pay_period_summary;
DROP TABLE IF EXISTS public_marts.fct_expense_group_summary;
DROP TABLE IF EXISTS public_marts.fct_budget_vs_actual;
DROP TABLE IF EXISTS public_marts.fct_savings_rate;
DROP TABLE IF EXISTS public_marts.fct_monthly_summary;
DROP VIEW IF EXISTS public_staging.stg_transactions;
DROP VIEW IF EXISTS public_staging.stg_categories;
DROP VIEW IF EXISTS public.v_monthly_summary;
DROP VIEW IF EXISTS public.v_budget_vs_actual;

-- ---------------------------------------------------------------------------
-- 1. TYPES: replace expense_groups with the four budgeting types.
-- ---------------------------------------------------------------------------
CREATE TABLE public.types (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name       VARCHAR(20) NOT NULL UNIQUE
               CHECK (name IN ('fixed', 'variable', 'income', 'saving')),
    sort_order INT NOT NULL UNIQUE CHECK (sort_order BETWEEN 1 AND 4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO public.types (name, sort_order) VALUES
    ('fixed',    1),
    ('variable', 2),
    ('income',   3),
    ('saving',   4);

-- ---------------------------------------------------------------------------
-- 2. CATEGORIES: replace type + expense_group_id with type_id.
-- ---------------------------------------------------------------------------
ALTER TABLE public.categories ADD COLUMN type_id UUID;

UPDATE public.categories c
SET type_id = t.id
FROM public.expense_groups eg
JOIN public.types t ON t.name = eg.name
WHERE c.expense_group_id = eg.id;

DO $category_check$
BEGIN
    IF EXISTS (SELECT 1 FROM public.categories WHERE type_id IS NULL) THEN
        RAISE EXCEPTION
            'Category migration failed: one or more categories have NULL type_id';
    END IF;
END
$category_check$;

ALTER TABLE public.categories ALTER COLUMN type_id SET NOT NULL;
ALTER TABLE public.categories
    ADD CONSTRAINT fk_categories_type
    FOREIGN KEY (type_id) REFERENCES public.types(id);

-- Supports a composite FK that guarantees a budget category belongs to its
-- declared type. The primary key still remains categories.id.
ALTER TABLE public.categories
    ADD CONSTRAINT uq_categories_id_type UNIQUE (id, type_id);

ALTER TABLE public.categories DROP COLUMN type;
ALTER TABLE public.categories DROP COLUMN expense_group_id;
ALTER TABLE public.categories DROP COLUMN IF EXISTS expense_group;

-- ---------------------------------------------------------------------------
-- 3. TRANSACTIONS: add bank-import lineage.
-- ---------------------------------------------------------------------------
ALTER TABLE public.transactions
    ADD COLUMN source VARCHAR(20) NOT NULL DEFAULT 'manual',
    ADD COLUMN raw_description VARCHAR(255),
    ADD COLUMN import_batch_id VARCHAR(50),
    ADD CONSTRAINT chk_transactions_source
        CHECK (source IN ('manual', 'bank_import'));

CREATE INDEX idx_transactions_import_batch
    ON public.transactions(import_batch_id)
    WHERE import_batch_id IS NOT NULL;

CREATE INDEX idx_transactions_import_dedup
    ON public.transactions(transaction_date, amount, raw_description)
    WHERE source = 'bank_import';

-- ---------------------------------------------------------------------------
-- 4. BUDGETS: unify per-category and type-envelope budgets.
-- ---------------------------------------------------------------------------
CREATE TABLE public.budgets (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type_id       UUID NOT NULL REFERENCES public.types(id),
    category_id   UUID,
    start_date    DATE NOT NULL,
    end_date      DATE NOT NULL DEFAULT '2030-01-01',
    budget_amount DECIMAL(10, 2) NOT NULL CHECK (budget_amount >= 0),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_budgets_date_range CHECK (end_date > start_date),
    CONSTRAINT fk_budgets_category_type
        FOREIGN KEY (category_id, type_id)
        REFERENCES public.categories(id, type_id)
);

-- Only one active row per category or type envelope. Historical rows may
-- coexist after their end_date is closed by the API.
CREATE UNIQUE INDEX idx_budgets_active_category
    ON public.budgets(type_id, category_id)
    WHERE category_id IS NOT NULL AND end_date = '2030-01-01';

CREATE UNIQUE INDEX idx_budgets_active_envelope
    ON public.budgets(type_id)
    WHERE category_id IS NULL AND end_date = '2030-01-01';

CREATE INDEX idx_budgets_category_dates
    ON public.budgets(category_id, start_date, end_date)
    WHERE category_id IS NOT NULL;

CREATE INDEX idx_budgets_envelope_dates
    ON public.budgets(type_id, start_date, end_date)
    WHERE category_id IS NULL;

-- ---------------------------------------------------------------------------
-- 5. IMPORT SUPPORT: merchant rules and detected pay dates.
-- ---------------------------------------------------------------------------
CREATE TABLE public.merchant_rules (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    keyword     VARCHAR(100) NOT NULL UNIQUE,
    category_id UUID NOT NULL REFERENCES public.categories(id),
    priority    INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO public.merchant_rules (keyword, category_id, priority) VALUES
    ('WOOLWORTHS', (SELECT id FROM public.categories WHERE name = 'Groceries'), 10),
    ('COLES', (SELECT id FROM public.categories WHERE name = 'Groceries'), 10),
    ('ALDI', (SELECT id FROM public.categories WHERE name = 'Groceries'), 10),
    ('OPTUS', (SELECT id FROM public.categories WHERE name = 'Phone & Internet'), 5),
    ('TELSTRA', (SELECT id FROM public.categories WHERE name = 'Phone & Internet'), 5),
    ('NETFLIX', (SELECT id FROM public.categories WHERE name = 'Subscriptions'), 5),
    ('SPOTIFY', (SELECT id FROM public.categories WHERE name = 'Subscriptions'), 5),
    ('UBER', (SELECT id FROM public.categories WHERE name = 'Transport'), 5),
    ('OPAL', (SELECT id FROM public.categories WHERE name = 'Transport'), 5),
    ('LINKT', (SELECT id FROM public.categories WHERE name = 'Transport'), 5),
    ('AMAZON', (SELECT id FROM public.categories WHERE name = 'Shopping'), 3),
    ('KMART', (SELECT id FROM public.categories WHERE name = 'Shopping'), 3),
    ('BUNNINGS', (SELECT id FROM public.categories WHERE name = 'Shopping'), 3),
    ('CHEMIST', (SELECT id FROM public.categories WHERE name = 'Health'), 3),
    ('MEDICARE', (SELECT id FROM public.categories WHERE name = 'Health'), 3),
    ('GYM', (SELECT id FROM public.categories WHERE name = 'Health'), 3),
    ('ENERGY', (SELECT id FROM public.categories WHERE name = 'Utilities'), 5),
    ('AGL', (SELECT id FROM public.categories WHERE name = 'Utilities'), 5),
    ('ORIGIN', (SELECT id FROM public.categories WHERE name = 'Utilities'), 5);

CREATE TABLE public.pay_dates (
    pay_date DATE PRIMARY KEY,
    source   VARCHAR(20) NOT NULL DEFAULT 'auto'
             CHECK (source IN ('auto', 'manual')),
    note     VARCHAR(100)
);

-- ---------------------------------------------------------------------------
-- 6. COPY AND VERIFY V2 BUDGET DATA BEFORE DROPPING LEGACY TABLES.
-- ---------------------------------------------------------------------------
INSERT INTO public.budgets (
    type_id, category_id, start_date, end_date, budget_amount
)
SELECT
    c.type_id,
    mb.category_id,
    mb.year_month,
    '2030-01-01',
    mb.budget_amount
FROM public.monthly_budgets mb
JOIN public.categories c ON c.id = mb.category_id;

INSERT INTO public.budgets (
    type_id, category_id, start_date, end_date, budget_amount
)
SELECT
    t.id,
    NULL,
    mgb.year_month,
    '2030-01-01',
    mgb.budget_amount
FROM public.monthly_group_budgets mgb
JOIN public.expense_groups eg ON eg.id = mgb.expense_group_id
JOIN public.types t ON t.name = eg.name;

DO $budget_copy_check$
BEGIN
    IF (
        SELECT COUNT(*)
        FROM public.budgets
        WHERE category_id IS NOT NULL
    ) <> (SELECT COUNT(*) FROM public.monthly_budgets) THEN
        RAISE EXCEPTION
            'Budget migration failed: category-budget row count changed';
    END IF;

    IF (
        SELECT COUNT(*)
        FROM public.budgets
        WHERE category_id IS NULL
    ) <> (SELECT COUNT(*) FROM public.monthly_group_budgets) THEN
        RAISE EXCEPTION
            'Budget migration failed: envelope-budget row count changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM public.monthly_budgets mb
        LEFT JOIN public.budgets b
            ON b.category_id = mb.category_id
           AND b.start_date = mb.year_month
           AND b.budget_amount = mb.budget_amount
        WHERE b.id IS NULL
    ) THEN
        RAISE EXCEPTION
            'Budget migration failed: category-budget values did not copy exactly';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM public.monthly_group_budgets mgb
        JOIN public.expense_groups eg ON eg.id = mgb.expense_group_id
        JOIN public.types t ON t.name = eg.name
        LEFT JOIN public.budgets b
            ON b.type_id = t.id
           AND b.category_id IS NULL
           AND b.start_date = mgb.year_month
           AND b.budget_amount = mgb.budget_amount
        WHERE b.id IS NULL
    ) THEN
        RAISE EXCEPTION
            'Budget migration failed: envelope-budget values did not copy exactly';
    END IF;
END
$budget_copy_check$;

-- No CASCADE: unexpected remaining dependencies should abort and roll back.
DROP TABLE public.monthly_group_budgets;
DROP TABLE public.monthly_budgets;
DROP TABLE public.expense_groups;

-- ---------------------------------------------------------------------------
-- 7. RLS AND GRANTS: preserve prototype access for anon and authenticated.
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS "Allow public read" ON public.dim_date;
CREATE POLICY "Allow public read" ON public.dim_date
    FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "Allow public all" ON public.categories;
CREATE POLICY "Allow public all" ON public.categories
    FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow public all" ON public.transactions;
CREATE POLICY "Allow public all" ON public.transactions
    FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow public all" ON public.savings_goals;
CREATE POLICY "Allow public all" ON public.savings_goals
    FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

ALTER TABLE public.types ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public all" ON public.types
    FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

ALTER TABLE public.budgets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public all" ON public.budgets
    FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

ALTER TABLE public.merchant_rules ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public all" ON public.merchant_rules
    FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

ALTER TABLE public.pay_dates ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public all" ON public.pay_dates
    FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

GRANT SELECT, INSERT, UPDATE, DELETE
    ON TABLE public.types, public.categories, public.transactions,
             public.budgets, public.merchant_rules, public.pay_dates,
             public.savings_goals
    TO anon, authenticated;

GRANT SELECT ON TABLE public.dim_date TO anon, authenticated;

-- ---------------------------------------------------------------------------
-- 8. PUBLIC VIEWS.
-- ---------------------------------------------------------------------------
CREATE VIEW public.v_monthly_summary
WITH (security_invoker = true) AS
SELECT
    DATE_TRUNC('month', t.transaction_date)::DATE AS month,
    ts.name AS type_name,
    c.name AS category_name,
    COUNT(*) AS transaction_count,
    SUM(t.amount) AS total_amount,
    AVG(t.amount) AS avg_amount
FROM public.transactions t
JOIN public.categories c ON c.id = t.category_id
JOIN public.types ts ON ts.id = c.type_id
GROUP BY DATE_TRUNC('month', t.transaction_date), ts.name, c.name;

CREATE VIEW public.v_budget_vs_actual
WITH (security_invoker = true) AS
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
FROM public.budgets b
JOIN public.categories c ON c.id = b.category_id
LEFT JOIN public.transactions t
    ON t.category_id = b.category_id
   AND t.transaction_date >= b.start_date
   AND t.transaction_date < b.end_date
WHERE b.category_id IS NOT NULL
  AND b.end_date = '2030-01-01'
GROUP BY DATE_TRUNC('month', t.transaction_date), c.name, b.budget_amount;

-- Consecutive salary dates define inclusive pay periods. Subtracting integer
-- 1 from a DATE keeps period_end typed as DATE rather than TIMESTAMP.
CREATE VIEW public.v_pay_periods
WITH (security_invoker = true) AS
SELECT
    pay_date AS period_start,
    COALESCE(
        LEAD(pay_date) OVER (ORDER BY pay_date) - 1,
        '2030-01-01'::DATE
    ) AS period_end
FROM public.pay_dates;

GRANT SELECT
    ON TABLE public.v_monthly_summary,
             public.v_budget_vs_actual,
             public.v_pay_periods
    TO anon, authenticated;

-- ---------------------------------------------------------------------------
-- 9. FINAL ASSERTIONS. COMMIT ONLY IF ALL EXPECTATIONS HOLD.
-- ---------------------------------------------------------------------------
DO $final_check$
BEGIN
    IF (SELECT COUNT(*) FROM public.types) <> 4 THEN
        RAISE EXCEPTION 'Final validation failed: expected exactly 4 types';
    END IF;

    IF EXISTS (SELECT 1 FROM public.categories WHERE type_id IS NULL) THEN
        RAISE EXCEPTION 'Final validation failed: category type_id is NULL';
    END IF;

    IF (SELECT COUNT(*) FROM public.merchant_rules) <> 19 THEN
        RAISE EXCEPTION 'Final validation failed: expected 19 merchant rules';
    END IF;

    IF to_regclass('public.expense_groups') IS NOT NULL
       OR to_regclass('public.monthly_budgets') IS NOT NULL
       OR to_regclass('public.monthly_group_budgets') IS NOT NULL THEN
        RAISE EXCEPTION 'Final validation failed: legacy V2 tables remain';
    END IF;

    IF to_regclass('public.v_monthly_summary') IS NULL
       OR to_regclass('public.v_budget_vs_actual') IS NULL
       OR to_regclass('public.v_pay_periods') IS NULL THEN
        RAISE EXCEPTION 'Final validation failed: one or more public views are missing';
    END IF;
END
$final_check$;

-- Ask PostgREST to expose the new relations immediately after commit.
NOTIFY pgrst, 'reload schema';

COMMIT;

-- ---------------------------------------------------------------------------
-- 10. READ-ONLY REPORTS (run only after the successful COMMIT above).
-- ---------------------------------------------------------------------------
SELECT 'types' AS object_name, COUNT(*) AS row_count FROM public.types
UNION ALL
SELECT 'budgets_total', COUNT(*) FROM public.budgets
UNION ALL
SELECT 'budgets_per_category', COUNT(*) FROM public.budgets WHERE category_id IS NOT NULL
UNION ALL
SELECT 'budgets_envelope', COUNT(*) FROM public.budgets WHERE category_id IS NULL
UNION ALL
SELECT 'categories_migrated', COUNT(*) FROM public.categories WHERE type_id IS NOT NULL
UNION ALL
SELECT 'merchant_rules', COUNT(*) FROM public.merchant_rules
UNION ALL
SELECT 'transactions_preserved', COUNT(*) FROM public.transactions
UNION ALL
SELECT 'pay_dates', COUNT(*) FROM public.pay_dates;

SELECT
    ts.name AS type_name,
    CASE WHEN b.category_id IS NULL THEN '-- ALL --' ELSE c.name END AS category_name,
    b.start_date,
    b.end_date,
    b.budget_amount,
    CASE WHEN b.end_date = '2030-01-01' THEN 'active' ELSE 'historical' END AS status
FROM public.budgets b
JOIN public.types ts ON ts.id = b.type_id
LEFT JOIN public.categories c ON c.id = b.category_id
ORDER BY ts.sort_order, b.category_id NULLS LAST, b.start_date;
