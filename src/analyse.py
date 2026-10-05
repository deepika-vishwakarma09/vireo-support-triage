"""Step 3: who is actually doing the work, and what does the misrouting cost?

Reads data/clean/tickets_labelled.csv (true_category from the categoriser) and writes tables to outputs/.
Three lenses on 'team volume':
  assigned   - the team the intake bot routed to (Priya's view)
  resolved   - the team of the agent who actually resolved it (label-free, from agents.csv)
  true owner - the team that SHOULD own it, from the true_category (depends on classifier accuracy ~90%)
"""
import os

import pandas as pd

LABELLED = "data/clean/tickets_labelled.csv"
OUT = "outputs"
TRANSFER_COST = 305          # Rs per transfer, policy section 4
HIRE_COST_TWO_PER_YEAR = 900000   # Arjun: two hires ~ Rs 9 lakh a year
FRONTLINE = {"chat": "Chat Frontline", "social": "Chat Frontline",
             "email": "Email Frontline", "voice": "Voice Frontline"}
OWNER = {   # policy section 6; Order Change & Cancellation -> Logistics is an assumption (see docs/decisions.md)
    "Delivery & Shipping": "Logistics", "Order Change & Cancellation": "Logistics",
    "Billing & Payments": "Billing", "Returns & Refunds": "Returns Desk",
    "Warranty & Repair": "Escalations & Warranty"}


def true_owner(row):
    return OWNER.get(row["true_category"]) or FRONTLINE[row["channel"]]


def avg_active_agents(months):
    """Average number of agents on the roster per team across the given months (roster has one row per assignment)."""
    a = pd.read_csv("data/raw/agents.csv", parse_dates=["from_date", "to_date"])
    rows = []
    for m in months:
        start = pd.Period(m).start_time
        end = pd.Period(m).end_time
        act = a[(a.from_date <= end) & (a.to_date.isna() | (a.to_date >= start))]
        rows.append(act.groupby("team").agent_id.nunique())
    return pd.concat(rows, axis=1).fillna(0).mean(axis=1)


def run():
    os.makedirs(OUT, exist_ok=True)
    t = pd.read_csv(LABELLED)
    t["true_owner"] = t.apply(true_owner, axis=1)
    months = sorted(t.month.unique())
    n_months = len(months)
    agents = avg_active_agents(months)
    f = []  # findings lines

    # 1. Team load under the three lenses
    asg = t.assigned_team.value_counts()
    res = t.agent_team.value_counts()
    own = t.true_owner.value_counts()
    team = pd.DataFrame({"assigned": asg, "resolved": res, "true_owner": own}).fillna(0)
    team["avg_agents"] = agents
    for c in ["assigned", "resolved", "true_owner"]:
        team[f"{c}_pct"] = (team[c] / len(t) * 100).round(1)
        team[f"{c}_per_agent_month"] = (team[c] / team["avg_agents"] / n_months).round(1)
    team.round(1).to_csv(f"{OUT}/team_load.csv")
    f.append(f"Tickets analysed: {len(t)} over {n_months} months (Jan 2025 - Jun 2026).")
    f.append("Tier 2 (Escalations & Warranty) is NOT comparable on volume (policy section 6); ignore its row for headcount.")

    # 2. Billing queue: what is really in it?
    b = t[t.assigned_team == "Billing"]
    comp = (b.true_category.value_counts(normalize=True) * 100).round(1)
    comp.to_csv(f"{OUT}/billing_queue_true_category.csv", header=["pct"])
    by_agent = (b.agent_team.value_counts(normalize=True) * 100).round(1)
    by_agent.to_csv(f"{OUT}/billing_queue_resolved_by.csv", header=["pct"])
    not_billing = (b.true_category != "Billing & Payments").mean() * 100
    f.append(f"Billing queue ({len(b)} tickets, {len(b)/len(t)*100:.1f}% of all): classifier says {not_billing:.0f}% are NOT billing issues.")
    f.append(f"Label-free check: {by_agent.get('Logistics', 0):.0f}% of tickets routed to Billing were resolved by a Logistics agent.")

    # 3. Bot tag vs true category
    pd.crosstab(t.category, t.true_category).to_csv(f"{OUT}/bot_tag_vs_true_category.csv")
    agree = (t.category == t.true_category).mean() * 100
    f.append(f"Bot tag agrees with the classifier label on {agree:.0f}% of tickets (hand-checked sample: about 73%).")

    # 4. Transfers (helpdesk rows only: legacy rows are blank, not zero)
    h = t[t.transfers.notna()]
    base = h[h.assigned_team != "Billing"].transfers.mean()
    bl = h[h.assigned_team == "Billing"]
    excess = bl.transfers.sum() - base * len(bl)
    h_months = h.month.nunique()
    per_q = excess / h_months * 3
    f.append(f"Transfers per ticket: Billing {bl.transfers.mean():.2f} vs {base:.2f} for every other team.")
    f.append(f"Excess Billing transfers: {excess:.0f} over {h_months} months = about {per_q:.0f} a quarter = Rs {per_q*TRANSFER_COST:,.0f} a quarter at Rs {TRANSFER_COST} each.")
    f.append(f"Two hires cost about Rs {HIRE_COST_TWO_PER_YEAR/100000:.0f} lakh a year (Rs {HIRE_COST_TWO_PER_YEAR/4:,.0f} a quarter).")

    # 5. Headcount lens (label-free and label-based), Tier 1 teams only
    tier1 = team.drop(index="Escalations & Warranty", errors="ignore")
    f.append("\nTickets per agent per month (Tier 1 teams):")
    f.append(tier1[["avg_agents", "assigned_per_agent_month", "resolved_per_agent_month",
                    "true_owner_per_agent_month"]].round(1).to_string())

    # 5b. Volume grew ~70% from Aug 2025 but headcount did not move, so the 18-month average understates today's load.
    recent_months = months[-6:]
    rt = t[t.month.isin(recent_months)]
    ragents = avg_active_agents(recent_months)
    rec = pd.DataFrame({"resolved": rt.agent_team.value_counts(), "true_owner": rt.true_owner.value_counts()}).fillna(0)
    rec["agents"] = ragents
    rec["resolved_per_agent_month"] = (rec.resolved / rec.agents / len(recent_months)).round(1)
    rec["true_owner_per_agent_month"] = (rec.true_owner / rec.agents / len(recent_months)).round(1)
    rec = rec.drop(index="Escalations & Warranty", errors="ignore")
    rec.to_csv(f"{OUT}/team_load_last6m.csv")
    f.append(f"\nLast 6 months only ({recent_months[0]} to {recent_months[-1]}), tickets per agent per month:")
    f.append(rec[["agents", "resolved_per_agent_month", "true_owner_per_agent_month"]].to_string())

    # 5c. Sensitivity: what if Order Change & Cancellation is NOT Logistics' work (goes to Frontline instead)?
    alt_owner = {k: v for k, v in OWNER.items() if k != "Order Change & Cancellation"}
    def alt(row):
        return alt_owner.get(row["true_category"]) or FRONTLINE[row["channel"]]
    alt_own = rt.apply(alt, axis=1).value_counts()
    alt_per_agent = (alt_own / ragents / len(recent_months)).round(1)
    f.append("\nSensitivity (Order Change & Cancellation treated as Frontline work), last 6 months, tickets per agent per month:")
    f.append(alt_per_agent.drop(index="Escalations & Warranty", errors="ignore").to_string())

    # 6. Monthly tables for charts
    t.groupby(["month", "category"]).size().unstack(fill_value=0).to_csv(f"{OUT}/monthly_by_bot_category.csv")
    t.groupby(["month", "true_category"]).size().unstack(fill_value=0).to_csv(f"{OUT}/monthly_by_true_category.csv")
    t.groupby(["month", "assigned_team"]).size().unstack(fill_value=0).to_csv(f"{OUT}/monthly_by_assigned_team.csv")
    t.groupby(["month", "agent_team"]).size().unstack(fill_value=0).to_csv(f"{OUT}/monthly_by_resolving_team.csv")
    t.groupby(["month", "true_owner"]).size().unstack(fill_value=0).to_csv(f"{OUT}/monthly_by_true_owner.csv")

    text = "\n".join(f)
    open(f"{OUT}/findings.txt", "w", encoding="utf-8").write(text)
    print(text)
    return team


if __name__ == "__main__":
    run()
