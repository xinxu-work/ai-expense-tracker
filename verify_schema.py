import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), 'api', '.env'))
from supabase import create_client

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

print("=" * 55)
print("VERIFYING STAR SCHEMA v3")
print("=" * 55)

errors = []

# 1. types table
types = supabase.table('types').select('*').order('sort_order').execute()
print(f"\n[1] types ({len(types.data)} rows):")
for t in types.data:
    print(f"  {t['id'][:8]}... | {t['name']:<10s} | sort_order={t['sort_order']}")
if len(types.data) != 4:
    errors.append(f"types: expected 4 rows, got {len(types.data)}")

# 2. categories with type_id FK → types
cats = supabase.table('categories').select('name, type_id, types!inner(name)').order('name').execute()
print(f"\n[2] categories ({len(cats.data)} rows) — FK → types:")
by_type = {}
for c in cats.data:
    tname = c['types']['name']
    by_type.setdefault(tname, []).append(c['name'])
for tname in ['fixed', 'variable', 'income', 'saving']:
    names = by_type.get(tname, [])
    print(f"  {tname:<10s} ({len(names)}): {', '.join(names)}")
if len(cats.data) < 22:
    errors.append(f"categories: expected 22+ rows, got {len(cats.data)}")

# 3. budgets table — per-category (active only: end_date = '2030-01-01')
cat_budgets = supabase.table('budgets').select('start_date, end_date, budget_amount, types(name), categories(name)').not_.is_('category_id', 'null').eq('end_date', '2030-01-01').execute()
print(f"\n[3] budgets — per-category (active, {len(cat_budgets.data)} rows):")
for b in cat_budgets.data:
    amt = float(b['budget_amount'])
    cname = b['categories']['name']
    tname = b['types']['name']
    print(f"  {b['start_date']} → {b['end_date']} | {tname} | {cname:<20s} | ${amt:,.0f}")

# 4. budgets table — envelope (category_id IS NULL, active only)
env_budgets = supabase.table('budgets').select('start_date, end_date, budget_amount, types(name)').is_('category_id', 'null').eq('end_date', '2030-01-01').execute()
print(f"\n[4] budgets — envelope (active, {len(env_budgets.data)} rows):")
for b in env_budgets.data:
    amt = float(b['budget_amount'])
    tname = b['types']['name']
    print(f"  {b['start_date']} → {b['end_date']} | {tname:<10s} | ENVELOPE | ${amt:,.0f}")

# 5. merchant_rules
rules = supabase.table('merchant_rules').select('keyword, categories(name), priority').order('priority', desc=True).execute()
print(f"\n[5] merchant_rules ({len(rules.data)} rows):")
for r in rules.data[:10]:  # show first 10
    print(f"  {r['keyword']:<20s} → {r['categories']['name']:<20s} (priority={r['priority']})")
if len(rules.data) < 5:
    errors.append(f"merchant_rules: expected 5+ seed rules, got {len(rules.data)}")

# 6. pay_dates
pay_dates = supabase.table('pay_dates').select('*').order('pay_date').execute()
print(f"\n[6] pay_dates ({len(pay_dates.data)} rows):")
for pd in pay_dates.data:
    print(f"  {pd['pay_date']} | source={pd['source']} | {pd.get('note', '')}")

# 7. v_pay_periods
periods = supabase.table('v_pay_periods').select('*').order('period_start').execute()
print(f"\n[7] v_pay_periods ({len(periods.data)} rows):")
for pp in periods.data:
    print(f"  {pp['period_start']} → {pp['period_end']}")

# 8. savings_goals
goals = supabase.table('savings_goals').select('*').execute()
print(f"\n[8] savings_goals ({len(goals.data)} rows):")
for g in goals.data:
    print(f"  {g['name']} | ${float(g['current_amount']):,.0f} / ${float(g['target_amount']):,.0f} | {g['status']}")

# 9. transactions FK → dim_date + categories
txns = supabase.table('transactions').select('id, amount, transaction_date, source, categories(name)').limit(5).execute()
print(f"\n[9] transactions (sample of 5, FK → dim_date + categories):")
for t in txns.data:
    print(f"  {str(t['transaction_date'])[:10]} | {t['source']:<12s} | {t['categories']['name']:<20s} | ${float(t['amount']):,.2f}")

# Summary
print("\n" + "=" * 55)
if errors:
    print(f"FAILED — {len(errors)} error(s):")
    for e in errors:
        print(f"  x {e}")
else:
    print("ALL CHECKS PASSED — Star Schema v3.1 is live")
print("=" * 55)
