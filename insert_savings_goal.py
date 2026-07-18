import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), 'api', '.env'))
from supabase import create_client

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

goal = {
    'name': 'Japan Trip November 2026',
    'target_amount': 1200,
    'current_amount': 0,
    'target_date': '2026-11-01',
    'status': 'active'
}
result = supabase.table('savings_goals').insert(goal).execute()
g = result.data[0]
print(f"Goal: {g['name']}")
print(f"Target: ${g['target_amount']:,.0f}")
print(f"Monthly deposit: ~$100 x 12 months")
print(f"ID: {g['id']}")

# Show all active goals
goals = supabase.table('savings_goals').select('*').eq('status', 'active').execute()
print()
for g in goals.data:
    pct = (g['current_amount'] / g['target_amount'] * 100) if g['target_amount'] > 0 else 0
    print(f"  {g['name']}")
    print(f"    Progress: ${g['current_amount']:,.0f} / ${g['target_amount']:,.0f} ({pct:.0f}%)")
    print(f"    Target date: {g['target_date']}")
