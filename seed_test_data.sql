-- ============================================
-- Test Data: 3 months of realistic expenses
-- Feb, Mar, Apr 2026
-- ============================================

-- Category IDs (from your Supabase)
-- Rent:              1b1ab8af-4246-4aa7-81aa-1accafd3e556
-- Groceries:         d3ce8f97-bfb7-4732-9e91-1aa3ee5676df
-- Dining Out:        8d9d6451-61ee-43aa-8251-6cbfdf1000bf
-- Transport:         075c92e1-e87b-4725-beb1-a65cbc3b4921
-- Utilities:         76cdd75a-93f8-4639-b70a-8dba24eb59a1
-- Phone & Internet:  064217b8-f40d-4705-8d68-8f627ce22c6c
-- Insurance:         8f63ad18-6446-47fa-945f-a427a691a0c4
-- Health:            18531b96-6749-477f-a124-f1b8ce59c0f2
-- Entertainment:     a27b63fa-1a26-4a1e-b087-487a3e8697cb
-- Shopping:          adb4c401-a163-449a-bbd2-5959dcf4ccc9
-- Subscriptions:     ee5903fd-0b18-4d45-bc47-bc6278af6db6
-- Personal Care:     43afc576-5ff8-4867-8ed9-f2e7244d7455
-- Salary:            10c5e283-09b8-4641-b724-e8cb875c4add
-- Freelance:         f8178c88-af40-4d39-9fc3-5f0e5c19e0a7
-- Investment:        4b7cdeee-7526-4ed0-98c5-1819dada6fb5
-- General Savings:   a0c3bc58-b87e-44e9-a18b-d7cebb3d6610
-- Emergency Fund:    b13286b5-7105-4ecb-a77d-43274f07948c
-- Investment Savings:1a7d8441-cdfb-473d-a3c5-6c28daaa6827

-- ==================== FEBRUARY 2026 ====================

-- Income
INSERT INTO transactions (transaction_date, category_id, amount, description, payment_method, is_recurring) VALUES
('2026-02-15', '10c5e283-09b8-4641-b724-e8cb875c4add', 5500.00, 'Feb salary', 'transfer', true),
('2026-02-28', '10c5e283-09b8-4641-b724-e8cb875c4add', 5500.00, 'Feb salary 2nd half', 'transfer', true),
('2026-02-20', 'f8178c88-af40-4d39-9fc3-5f0e5c19e0a7', 800.00, 'Freelance data project', 'transfer', false);

-- Savings
INSERT INTO transactions (transaction_date, category_id, amount, description, payment_method, is_recurring) VALUES
('2026-02-16', 'a0c3bc58-b87e-44e9-a18b-d7cebb3d6610', 1000.00, 'Monthly savings transfer', 'transfer', true),
('2026-02-16', 'b13286b5-7105-4ecb-a77d-43274f07948c', 500.00, 'Emergency fund contribution', 'transfer', true),
('2026-02-16', '1a7d8441-cdfb-473d-a3c5-6c28daaa6827', 300.00, 'ETF investment', 'transfer', true);

-- Expenses
INSERT INTO transactions (transaction_date, category_id, amount, description, payment_method, is_recurring) VALUES
('2026-02-01', '1b1ab8af-4246-4aa7-81aa-1accafd3e556', 2200.00, 'Feb rent', 'direct_debit', true),
('2026-02-03', 'd3ce8f97-bfb7-4732-9e91-1aa3ee5676df', 92.30, 'Woolworths weekly shop', 'card', false),
('2026-02-10', 'd3ce8f97-bfb7-4732-9e91-1aa3ee5676df', 78.50, 'Coles groceries', 'card', false),
('2026-02-17', 'd3ce8f97-bfb7-4732-9e91-1aa3ee5676df', 105.20, 'Woolworths weekly shop', 'card', false),
('2026-02-24', 'd3ce8f97-bfb7-4732-9e91-1aa3ee5676df', 88.90, 'Aldi groceries', 'card', false),
('2026-02-05', '8d9d6451-61ee-43aa-8251-6cbfdf1000bf', 45.00, 'Dinner with friends - Thai', 'card', false),
('2026-02-14', '8d9d6451-61ee-43aa-8251-6cbfdf1000bf', 120.00, 'Valentines dinner', 'card', false),
('2026-02-22', '8d9d6451-61ee-43aa-8251-6cbfdf1000bf', 32.50, 'Lunch at cafe', 'card', false),
('2026-02-02', '075c92e1-e87b-4725-beb1-a65cbc3b4921', 60.00, 'Opal card top-up', 'card', false),
('2026-02-16', '075c92e1-e87b-4725-beb1-a65cbc3b4921', 60.00, 'Opal card top-up', 'card', false),
('2026-02-10', '76cdd75a-93f8-4639-b70a-8dba24eb59a1', 185.00, 'Electricity bill', 'direct_debit', false),
('2026-02-15', '064217b8-f40d-4705-8d68-8f627ce22c6c', 89.00, 'Optus phone + internet', 'direct_debit', true),
('2026-02-01', '8f63ad18-6446-47fa-945f-a427a691a0c4', 145.00, 'Health insurance', 'direct_debit', true),
('2026-02-08', '18531b96-6749-477f-a124-f1b8ce59c0f2', 65.00, 'GP visit', 'card', false),
('2026-02-12', 'a27b63fa-1a26-4a1e-b087-487a3e8697cb', 25.00, 'Movie tickets', 'card', false),
('2026-02-20', 'adb4c401-a163-449a-bbd2-5959dcf4ccc9', 79.00, 'New running shoes (sale)', 'card', false),
('2026-02-01', 'ee5903fd-0b18-4d45-bc47-bc6278af6db6', 22.99, 'Netflix + Spotify', 'card', true),
('2026-02-18', '43afc576-5ff8-4867-8ed9-f2e7244d7455', 35.00, 'Haircut', 'cash', false);

-- ==================== MARCH 2026 ====================

-- Income
INSERT INTO transactions (transaction_date, category_id, amount, description, payment_method, is_recurring) VALUES
('2026-03-15', '10c5e283-09b8-4641-b724-e8cb875c4add', 5500.00, 'Mar salary', 'transfer', true),
('2026-03-31', '10c5e283-09b8-4641-b724-e8cb875c4add', 5500.00, 'Mar salary 2nd half', 'transfer', true),
('2026-03-10', '4b7cdeee-7526-4ed0-98c5-1819dada6fb5', 120.00, 'Dividend payment', 'transfer', false);

-- Savings
INSERT INTO transactions (transaction_date, category_id, amount, description, payment_method, is_recurring) VALUES
('2026-03-16', 'a0c3bc58-b87e-44e9-a18b-d7cebb3d6610', 1200.00, 'Monthly savings transfer', 'transfer', true),
('2026-03-16', 'b13286b5-7105-4ecb-a77d-43274f07948c', 500.00, 'Emergency fund contribution', 'transfer', true),
('2026-03-16', '1a7d8441-cdfb-473d-a3c5-6c28daaa6827', 400.00, 'ETF investment', 'transfer', true);

-- Expenses
INSERT INTO transactions (transaction_date, category_id, amount, description, payment_method, is_recurring) VALUES
('2026-03-01', '1b1ab8af-4246-4aa7-81aa-1accafd3e556', 2200.00, 'Mar rent', 'direct_debit', true),
('2026-03-02', 'd3ce8f97-bfb7-4732-9e91-1aa3ee5676df', 95.60, 'Woolworths weekly shop', 'card', false),
('2026-03-09', 'd3ce8f97-bfb7-4732-9e91-1aa3ee5676df', 82.30, 'Coles groceries', 'card', false),
('2026-03-16', 'd3ce8f97-bfb7-4732-9e91-1aa3ee5676df', 110.40, 'Woolworths weekly shop', 'card', false),
('2026-03-23', 'd3ce8f97-bfb7-4732-9e91-1aa3ee5676df', 73.80, 'Aldi groceries', 'card', false),
('2026-03-30', 'd3ce8f97-bfb7-4732-9e91-1aa3ee5676df', 98.50, 'Woolworths weekly shop', 'card', false),
('2026-03-06', '8d9d6451-61ee-43aa-8251-6cbfdf1000bf', 55.00, 'Korean BBQ with mates', 'card', false),
('2026-03-15', '8d9d6451-61ee-43aa-8251-6cbfdf1000bf', 28.00, 'Lunch - pho', 'card', false),
('2026-03-21', '8d9d6451-61ee-43aa-8251-6cbfdf1000bf', 68.00, 'Birthday dinner out', 'card', false),
('2026-03-28', '8d9d6451-61ee-43aa-8251-6cbfdf1000bf', 18.50, 'Coffee catch-up', 'card', false),
('2026-03-01', '075c92e1-e87b-4725-beb1-a65cbc3b4921', 60.00, 'Opal card top-up', 'card', false),
('2026-03-15', '075c92e1-e87b-4725-beb1-a65cbc3b4921', 60.00, 'Opal card top-up', 'card', false),
('2026-03-25', '075c92e1-e87b-4725-beb1-a65cbc3b4921', 45.00, 'Uber to airport', 'card', false),
('2026-03-08', '76cdd75a-93f8-4639-b70a-8dba24eb59a1', 65.00, 'Water bill', 'direct_debit', false),
('2026-03-20', '76cdd75a-93f8-4639-b70a-8dba24eb59a1', 120.00, 'Gas bill', 'direct_debit', false),
('2026-03-15', '064217b8-f40d-4705-8d68-8f627ce22c6c', 89.00, 'Optus phone + internet', 'direct_debit', true),
('2026-03-01', '8f63ad18-6446-47fa-945f-a427a691a0c4', 145.00, 'Health insurance', 'direct_debit', true),
('2026-03-12', '18531b96-6749-477f-a124-f1b8ce59c0f2', 250.00, 'Dentist check-up', 'card', false),
('2026-03-07', 'a27b63fa-1a26-4a1e-b087-487a3e8697cb', 35.00, 'Concert tickets', 'card', false),
('2026-03-22', 'a27b63fa-1a26-4a1e-b087-487a3e8697cb', 15.00, 'Bowling night', 'card', false),
('2026-03-14', 'adb4c401-a163-449a-bbd2-5959dcf4ccc9', 199.00, 'Uniqlo haul', 'card', false),
('2026-03-01', 'ee5903fd-0b18-4d45-bc47-bc6278af6db6', 22.99, 'Netflix + Spotify', 'card', true),
('2026-03-05', '43afc576-5ff8-4867-8ed9-f2e7244d7455', 35.00, 'Haircut', 'cash', false);

-- ==================== APRIL 2026 ====================

-- Income
INSERT INTO transactions (transaction_date, category_id, amount, description, payment_method, is_recurring) VALUES
('2026-04-01', '10c5e283-09b8-4641-b724-e8cb875c4add', 5800.00, 'Apr salary (incl. bonus)', 'transfer', true),
('2026-04-05', 'f8178c88-af40-4d39-9fc3-5f0e5c19e0a7', 1200.00, 'Freelance dashboard project', 'transfer', false);

-- Savings
INSERT INTO transactions (transaction_date, category_id, amount, description, payment_method, is_recurring) VALUES
('2026-04-02', 'a0c3bc58-b87e-44e9-a18b-d7cebb3d6610', 1500.00, 'Monthly savings (extra from bonus)', 'transfer', true),
('2026-04-02', 'b13286b5-7105-4ecb-a77d-43274f07948c', 500.00, 'Emergency fund contribution', 'transfer', true),
('2026-04-02', '1a7d8441-cdfb-473d-a3c5-6c28daaa6827', 500.00, 'ETF investment', 'transfer', true);

-- Expenses
INSERT INTO transactions (transaction_date, category_id, amount, description, payment_method, is_recurring) VALUES
('2026-04-01', '1b1ab8af-4246-4aa7-81aa-1accafd3e556', 2200.00, 'Apr rent', 'direct_debit', true),
('2026-04-03', 'd3ce8f97-bfb7-4732-9e91-1aa3ee5676df', 88.70, 'Woolworths weekly shop', 'card', false),
('2026-04-10', 'd3ce8f97-bfb7-4732-9e91-1aa3ee5676df', 102.40, 'Coles groceries', 'card', false),
('2026-04-07', '8d9d6451-61ee-43aa-8251-6cbfdf1000bf', 42.00, 'Ramen with colleagues', 'card', false),
('2026-04-12', '8d9d6451-61ee-43aa-8251-6cbfdf1000bf', 55.00, 'Saturday brunch', 'card', false),
('2026-04-01', '075c92e1-e87b-4725-beb1-a65cbc3b4921', 60.00, 'Opal card top-up', 'card', false),
('2026-04-10', '76cdd75a-93f8-4639-b70a-8dba24eb59a1', 195.00, 'Electricity bill (winter coming)', 'direct_debit', false),
('2026-04-01', '064217b8-f40d-4705-8d68-8f627ce22c6c', 89.00, 'Optus phone + internet', 'direct_debit', true),
('2026-04-01', '8f63ad18-6446-47fa-945f-a427a691a0c4', 145.00, 'Health insurance', 'direct_debit', true),
('2026-04-08', 'a27b63fa-1a26-4a1e-b087-487a3e8697cb', 22.00, 'Stan subscription', 'card', false),
('2026-04-01', 'ee5903fd-0b18-4d45-bc47-bc6278af6db6', 22.99, 'Netflix + Spotify', 'card', true),
('2026-04-14', 'd3ce8f97-bfb7-4732-9e91-1aa3ee5676df', 85.50, 'Weekly groceries at Woolworths', 'card', false);

-- ==================== BUDGETS (v3 — SCD Type 2) ====================
-- Per-category budgets for fixed expenses (end_date defaults to '2030-01-01')
INSERT INTO budgets (type_id, category_id, start_date, budget_amount)
SELECT
    (SELECT id FROM types WHERE name = 'fixed') AS type_id,
    c.id,
    '2026-04-01',
    b.budget
FROM categories c
JOIN (VALUES
    ('Rent',              2200.00),
    ('Groceries',          400.00),
    ('Dining Out',         150.00),
    ('Transport',          150.00),
    ('Utilities',          200.00),
    ('Phone & Internet',    89.00),
    ('Insurance',          145.00),
    ('Entertainment',      100.00),
    ('Subscriptions',       25.00),
    ('Shopping',           150.00)
) AS b(name, budget) ON c.name = b.name;

-- Envelope budget for variable type
INSERT INTO budgets (type_id, category_id, start_date, budget_amount)
SELECT id, NULL, '2026-04-01', 1700
FROM types WHERE name = 'variable'
ON CONFLICT (type_id) WHERE category_id IS NULL AND end_date = '2030-01-01' DO NOTHING;

-- ==================== SAVINGS GOALS ====================

INSERT INTO savings_goals (name, target_amount, current_amount, target_date, status) VALUES
('Emergency Fund (6 months expenses)', 30000.00, 12500.00, '2027-06-01', 'active'),
('Japan Trip 2027', 8000.00, 2200.00, '2027-03-01', 'active'),
('Investment Portfolio', 50000.00, 15800.00, '2028-12-31', 'active');
