import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), 'api', '.env'))
from supabase import create_client

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# 1. Insert/update variable envelope budget (SCD Type 2: end_date = '2030-01-01')
var_type = supabase.table('types').select('id').eq('name', 'variable').single().execute()
var_type_id = var_type.data['id']

result = supabase.table('budgets').select('*').eq('type_id', var_type_id).is_('category_id', 'null').eq('end_date', '2030-01-01').execute()
if result.data:
    row_id = result.data[0]['id']
    supabase.table('budgets').update({'budget_amount': 1700, 'start_date': '2026-04-01'}).eq('id', row_id).execute()
    print('[1] Variable envelope budget updated')
else:
    supabase.table('budgets').insert({
        'type_id': var_type_id,
        'category_id': None,
        'start_date': '2026-04-01',
        'budget_amount': 1700
    }).execute()
    print('[1] Variable envelope budget inserted')

# 2. Delete duplicate savings goal
supabase.table('savings_goals').delete().eq('id', 'e4459285-aa52-4432-bea1-11b2cf5d8d49').execute()
print('[2] Duplicate savings goal deleted')

# 3. Final state
print()
print('=' * 50)
print('FINAL DATABASE STATE')
print('=' * 50)

gb_check = supabase.table('budgets').select('*, types(name)').is_('category_id', 'null').eq('end_date', '2030-01-01').execute()
for g in gb_check.data:
    amt = float(g['budget_amount'])
    tname = g['types']['name']
    print(f"Envelope budget: {tname} = ${amt:,.0f} (since {g['start_date']})")

budgets = supabase.table('budgets').select('budget_amount, categories(name), types(name)').not_.is_('category_id', 'null').eq('end_date', '2030-01-01').execute()
total_fixed = 0
for b in budgets.data:
    amt = float(b['budget_amount'])
    name = b['categories']['name']
    total_fixed += amt
    print(f"Category budget: {name} = ${amt:,.0f}")

grand_total = total_fixed + 1700
print(f"\nFixed total:       ${total_fixed:,.0f}")
print(f"Variable total:    $1,700")
print(f"Monthly budget:    ${grand_total:,.0f}")
print(f"Expected savings:  ${6760 - grand_total:,.0f} (of $6,760 income)")

goals = supabase.table('savings_goals').select('*').eq('status', 'active').execute()
print(f"\nActive savings goals: {len(goals.data)}")
for g in goals.data:
    pct = float(g['current_amount']) / float(g['target_amount']) * 100
    print(f"  {g['name']} | ${float(g['current_amount']):,.0f}/{float(g['target_amount']):,.0f} ({pct:.0f}%)")
