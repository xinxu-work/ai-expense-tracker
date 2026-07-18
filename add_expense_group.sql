-- DEPRECATED in v3 (2026-06-23)
-- This script added expense_group VARCHAR column to categories and created
-- monthly_group_budgets table in v1. Both were replaced:
--   expense_groups → types
--   monthly_group_budgets + monthly_budgets → budgets (unified)
-- Run star_schema_v3_migration.sql instead.

-- Original script preserved for history:

-- Add expense_group to categories + create group-level budgets
-- Run this in Supabase SQL Editor:
-- https://supabase.com/dashboard/project/meluzsqwjzrsmmhimtpk/sql/new

-- 1. Add expense_group column
ALTER TABLE categories ADD COLUMN IF NOT EXISTS expense_group VARCHAR(20);

-- 2. Tag all categories
UPDATE categories SET expense_group = 'fixed'
WHERE name IN ('Rent', 'Utilities', 'Phone & Internet', 'Health', 'Insurance', 'Subscriptions');

UPDATE categories SET expense_group = 'variable'
WHERE name IN ('Groceries', 'Dining Out', 'Transport', 'Entertainment', 'Shopping', 'Personal Care', 'Other Expense', 'Education');

UPDATE categories SET expense_group = 'income'
WHERE name IN ('Salary', 'Freelance', 'Investment', 'Other Income');

UPDATE categories SET expense_group = 'saving'
WHERE name IN ('Emergency Fund', 'Investment Savings', 'Travel Fund', 'General Savings');

-- 3. Create monthly_group_budgets table
CREATE TABLE IF NOT EXISTS monthly_group_budgets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    expense_group VARCHAR(20) NOT NULL,
    year_month DATE NOT NULL,
    budget_amount DECIMAL(10, 2) NOT NULL CHECK (budget_amount >= 0),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(expense_group, year_month)
);

-- 4. Enable RLS
ALTER TABLE monthly_group_budgets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for authenticated" ON monthly_group_budgets
    FOR ALL USING (auth.role() = 'authenticated');

-- 5. Insert April 2026 budgets
-- Fixed expenses (category-level)
INSERT INTO monthly_budgets (category_id, year_month, budget_amount)
SELECT id, '2026-04-01', budget
FROM (
    VALUES
        ('Rent', 1700),
        ('Utilities', 150),
        ('Phone & Internet', 115),
        ('Health', 112),
        ('Insurance', 70),
        ('Subscriptions', 75)
) AS b(name, budget)
JOIN categories c ON c.name = b.name
ON CONFLICT (category_id, year_month) DO UPDATE SET budget_amount = EXCLUDED.budget_amount;

-- 6. Insert variable expenses group budget ($1,700)
INSERT INTO monthly_group_budgets (expense_group, year_month, budget_amount)
VALUES ('variable', '2026-04-01', 1700)
ON CONFLICT (expense_group, year_month) DO UPDATE SET budget_amount = EXCLUDED.budget_amount;

-- 7. Verify
SELECT expense_group, COUNT(*) as categories FROM categories GROUP BY expense_group;
