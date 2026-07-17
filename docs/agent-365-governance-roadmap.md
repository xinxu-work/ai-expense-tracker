# Agent 365 Governance Roadmap

Agent 365 is intentionally **not a runtime dependency** for the personal
portfolio version. Microsoft Foundry builds and runs the Expense Tracker agent.
The purchase-advice feature uses FastAPI as its controlled financial-rules
boundary; the older read-only agent tools still query Supabase directly.

## Current architecture

```text
User -> Foundry ExpenseTrackerAssistant -> affordability FastAPI tool -> Supabase
                                                           |
                                                           +-> activity_id
```

The purchase-advice flow is governance-ready in two ways:

1. The model calls `POST /advice/can-i-afford`; budget rules are deterministic
   application code, not an LLM calculation.
2. Each affordability check returns an `activity_id` that can later correlate
   application logs with agent activity and audit records.

## Future Agent 365 architecture

```text
User signs in with Microsoft Entra ID
              |
              v
Foundry agent published/onboarded to Agent 365
              |
              v
FastAPI validates delegated user + agent identity
              |
              v
Supabase applies user-level data access
              |
              v
Agent 365 receives configured activity/observability data
```

## Adoption checklist

- Confirm Agent 365 availability, preview terms, and licensing for the tenant.
- Publish/onboard `ExpenseTrackerAssistant` and capture its Agent ID and
  Blueprint ID in deployment configuration; never hard-code credentials.
- Replace the personal Supabase key flow with Microsoft Entra OAuth/OIDC for the
  frontend and FastAPI.
- Move the remaining direct-Supabase read tools behind authenticated FastAPI
  endpoints so every agent data access has one policy and audit boundary.
- Define least-privilege scopes such as `expenses.read`, `budgets.read`, and
  `expenses.write`.
- Require explicit user confirmation for write tools such as creating a
  transaction, changing a budget, or submitting a reimbursement.
- Propagate the human-user identity, agent identity, and `activity_id` through
  FastAPI logs without recording receipt contents or other sensitive payloads.
- Configure Agent 365 activity collection, monitoring, security policies, and
  retention according to the organisation's compliance requirements.
- Test suspend/revoke and incident-response paths before enabling write tools.

## Portfolio narrative

> Built a Microsoft Foundry personal-finance agent that uses deterministic
> FastAPI tools to assess purchases against category or envelope budgets. The
> architecture is prepared for future Agent 365 onboarding through a controlled
> API boundary, correlated activity IDs, least-privilege scopes, and explicit
> confirmation for financial write actions.
