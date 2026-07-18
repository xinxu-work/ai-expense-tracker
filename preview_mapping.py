import pandas as pd
import sys
sys.stdout.reconfigure(encoding='utf-8')

EXCEL = r'c:\Users\XinXu\iCloudDrive\Xin_Xin_File\DS\Import\Living_Expense_Mar.xlsx'
df = pd.read_excel(EXCEL, header=None)
headers = df.iloc[0].tolist()
march = df.iloc[1].tolist()
row = {headers[i]: march[i] for i in range(len(headers))}

MAPPING = [
    ('工资', 'Salary', '2026-03-16', 'Monthly salary'),
    ('房租', 'Rent', '2026-03-18', 'Monthly rent'),
    ('Gym', 'Health', '2026-03-16', 'Gym membership'),
    ('Health insurance', 'Insurance', '2026-03-20', 'Health insurance'),
    ('Mobile plan', 'Phone & Internet', '2026-03-20', 'Mobile plan'),
    ('Net Bill', 'Phone & Internet', '2026-03-22', 'Internet bill'),
    ('Apple bill', 'Subscriptions', '2026-03-22', 'Apple subscription'),
    ('Google bill', 'Subscriptions', '2026-03-22', 'Google subscription'),
    ('Netmusic bill', 'Subscriptions', '2026-03-22', 'NetEase Music subscription'),
    ('Notion', 'Subscriptions', '2026-03-22', 'Notion subscription'),
    ('CLAUDE', 'Subscriptions', '2026-03-22', 'Claude AI subscription'),
    ('Linkt', 'Transport', '2026-03-25', 'Linkt toll'),
    ('Transport', 'Transport', '2026-03-25', 'Public transport'),
    ('Fuel', 'Transport', '2026-03-28', 'Fuel'),
    ('Uber', 'Transport', '2026-03-27', 'Uber ride'),
    ('Ticket', 'Entertainment', '2026-04-02', 'Event ticket'),
    ('Other', 'Other Expense', '2026-04-01', 'Miscellaneous expense'),
]

CBA = [
    (300.00, 'Groceries', '2026-03-20', 'Groceries (CBA)'),
    (150.00, 'Dining Out', '2026-03-24', 'Dining out (CBA)'),
    (100.00, 'Other Expense', '2026-04-02', 'Transfer to friend (CBA)'),
    (15.80, 'Other Expense', '2026-04-05', 'Other spending (CBA)'),
]

ING = [
    (60.00, 'Entertainment', '2026-03-27', 'Entertainment (ING) [PLACEHOLDER]'),
    (40.00, 'Shopping', '2026-04-03', 'Shopping (ING) [PLACEHOLDER]'),
]

ING_J = [
    (200.00, 'Groceries', '2026-03-21', 'Groceries joint (ING Joint) [PLACEHOLDER]'),
    (150.00, 'Utilities', '2026-03-23', 'Utilities joint (ING Joint) [PLACEHOLDER]'),
    (100.00, 'Dining Out', '2026-04-01', 'Dining out joint (ING Joint) [PLACEHOLDER]'),
]

print('=== INCOME ===')
total_in = 0
for col, cat, dt, desc in MAPPING:
    val = row.get(col)
    if pd.notna(val) and val != 0 and cat == 'Salary':
        print(f'{dt} | +${float(val):,.2f} | {cat} -- {desc}')
        total_in += float(val)

print()
print('=== EXPENSES (Direct from columns) ===')
total_dir = 0
txn_count = 0
for col, cat, dt, desc in MAPPING:
    val = row.get(col)
    if pd.notna(val) and val != 0 and cat != 'Salary':
        print(f'{dt} | ${float(val):>7.2f} | {cat:<20s} | {desc}')
        total_dir += float(val)
        txn_count += 1

print()
print('=== EXPENSES (CBA $565.80 -> 4 txns) ===')
for amt, cat, dt, desc in CBA:
    print(f'{dt} | ${amt:>7.2f} | {cat:<20s} | {desc}')
    txn_count += 1

print()
print('=== EXPENSES (ING $100.00 -> 2 txns) ===')
for amt, cat, dt, desc in ING:
    print(f'{dt} | ${amt:>7.2f} | {cat:<20s} | {desc}')
    txn_count += 1

print()
print('=== EXPENSES (ING Joint $450.00 -> 3 txns) ===')
for amt, cat, dt, desc in ING_J:
    print(f'{dt} | ${amt:>7.2f} | {cat:<20s} | {desc}')
    txn_count += 1

total_out = total_dir + 565.80 + 100 + 450
rem = row.get('剩余', 0)

print()
print('=' * 60)
print(f'INCOME:     +${total_in:,.2f}')
print(f'EXPENSES:   -${total_out:,.2f}')
print(f'            {"-" * 20}')
print(f'NET:        ${total_in - total_out:,.2f}')
if pd.notna(rem):
    print(f'Excel rem:   ${rem:,.2f}')
print(f'Total transactions: {txn_count + 1} ({txn_count} expense + 1 income)')
