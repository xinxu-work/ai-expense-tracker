-- Star Schema v2: Proper expense_groups dimension with UUID FKs
-- Replaces text-based expense_group with FK links
-- Run in: https://supabase.com/dashboard/project/meluzsqwjzrsmmhimtpk/sql/new

-- ============================================
-- 0. DROP dependent dbt objects so old columns can be removed
--    staging = views, marts = tables
-- ============================================
DROP VIEW IF EXISTS public_staging.stg_categories CASCADE;
DROP VIEW IF EXISTS public_staging.stg_transactions CASCADE;
DROP TABLE IF EXISTS public_marts.fct_monthly_summary CASCADE;
DROP TABLE IF EXISTS public_marts.fct_savings_rate CASCADE;
DROP TABLE IF EXISTS public_marts.fct_budget_vs_actual CASCADE;
DROP TABLE IF EXISTS public_marts.fct_expense_group_summary CASCADE;

-- ============================================
-- 1. CREATE expense_groups dimension table
-- ============================================
CREATE TABLE IF NOT EXISTS expense_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(20) NOT NULL UNIQUE,
    type VARCHAR(10) NOT NULL CHECK (type IN ('expense', 'income', 'saving')),
    sort_order INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed the 4 groups (skip if already exist)
INSERT INTO expense_groups (name, type, sort_order) VALUES
    ('fixed', 'expense', 1),
    ('variable', 'expense', 2),
    ('income', 'income', 3),
    ('saving', 'saving', 4)
ON CONFLICT (name) DO NOTHING;

-- ============================================
-- 2. MIGRATE categories: expense_group VARCHAR -> expense_group_id UUID FK
-- ============================================

-- Add new UUID column (nullable first)
ALTER TABLE categories ADD COLUMN IF NOT EXISTS expense_group_id UUID;

-- Populate from text value
UPDATE categories c
SET expense_group_id = eg.id
FROM expense_groups eg
WHERE c.expense_group = eg.name;

-- Verify all categories were mapped
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM categories WHERE expense_group_id IS NULL) THEN
        RAISE EXCEPTION 'Some categories have NULL expense_group_id — check mapping';
    END IF;
END $$;

-- Make NOT NULL
ALTER TABLE categories ALTER COLUMN expense_group_id SET NOT NULL;

-- Add FK constraint
ALTER TABLE categories
ADD CONSTRAINT fk_categories_expense_group
FOREIGN KEY (expense_group_id) REFERENCES expense_groups(id);

-- Drop old text column
ALTER TABLE categories DROP COLUMN IF EXISTS expense_group;

-- ============================================
-- 3. MIGRATE monthly_group_budgets: expense_group VARCHAR -> expense_group_id UUID FK
-- ============================================

ALTER TABLE monthly_group_budgets ADD COLUMN IF NOT EXISTS expense_group_id UUID;

UPDATE monthly_group_budgets mgb
SET expense_group_id = eg.id
FROM expense_groups eg
WHERE mgb.expense_group = eg.name;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM monthly_group_budgets WHERE expense_group_id IS NULL) THEN
        RAISE EXCEPTION 'Some group budgets have NULL expense_group_id';
    END IF;
END $$;

ALTER TABLE monthly_group_budgets ALTER COLUMN expense_group_id SET NOT NULL;

ALTER TABLE monthly_group_budgets
ADD CONSTRAINT fk_group_budgets_expense_group
FOREIGN KEY (expense_group_id) REFERENCES expense_groups(id);

-- Drop old unique constraint (on text column)
ALTER TABLE monthly_group_budgets
DROP CONSTRAINT IF EXISTS monthly_group_budgets_expense_group_year_month_key;

-- Add new unique constraint (on UUID column)
ALTER TABLE monthly_group_budgets
ADD CONSTRAINT monthly_group_budgets_group_year_month_key
UNIQUE (expense_group_id, year_month);

-- Drop old text column
ALTER TABLE monthly_group_budgets DROP COLUMN IF EXISTS expense_group;

-- ============================================
-- 4. FK: transactions.transaction_date -> dim_date.date
-- ============================================
ALTER TABLE transactions
DROP CONSTRAINT IF EXISTS fk_transactions_date;
ALTER TABLE transactions
ADD CONSTRAINT fk_transactions_date
FOREIGN KEY (transaction_date) REFERENCES dim_date(date);

-- ============================================
-- 5. Auto-update trigger for expense_groups
-- ============================================
DROP TRIGGER IF EXISTS trigger_expense_groups_updated ON expense_groups;
CREATE TRIGGER trigger_expense_groups_updated
    BEFORE UPDATE ON expense_groups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================
-- 6. RLS for expense_groups
-- ============================================
ALTER TABLE expense_groups ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public all" ON expense_groups;
CREATE POLICY "Allow public all" ON expense_groups
    FOR ALL TO anon USING (true) WITH CHECK (true);

-- ============================================
-- 7. VERIFY
-- ============================================
SELECT 'expense_groups' AS tbl, COUNT(*) AS rows FROM expense_groups
UNION ALL
SELECT 'categories', COUNT(*) FROM categories WHERE expense_group_id IS NOT NULL
UNION ALL
SELECT 'monthly_group_budgets', COUNT(*) FROM monthly_group_budgets WHERE expense_group_id IS NOT NULL
UNION ALL
SELECT 'FKs', COUNT(*) FROM information_schema.table_constraints
    WHERE table_schema = 'public' AND constraint_type = 'FOREIGN KEY';

-- Show final mapping
SELECT eg.name AS group_name, c.name AS category_name
FROM expense_groups eg
JOIN categories c ON c.expense_group_id = eg.id
ORDER BY eg.sort_order, c.name;

-- Show group budgets
SELECT eg.name AS group_name, mgb.year_month, mgb.budget_amount
FROM expense_groups eg
JOIN monthly_group_budgets mgb ON mgb.expense_group_id = eg.id;
