
"""Step 1: clean the raw client exports and write data/clean/tickets_clean.csv.

Every decision here is also written up in docs/decisions.md.
"""
import os
import pandas as pd

RAW = "data/raw"
CLEAN = "data/clean"
IST_OFFSET = pd.Timedelta(hours=5, minutes=30)
# Tickets before this date are a stray extract (139 rows, all Billing-tagged,
# README says the data starts Jan 2025). Excluded so Billing share is not inflated.
START_DATE = "2025-01-01"
# First-response targets from support-policy.pdf section 3
SLA_MINUTES = {"chat": 15, "voice": 120, "social": 240, "email": 480}


def load():
    t = pd.read_csv(f"{RAW}/tickets.csv",
                    parse_dates=["created_at", "first_response_at", "resolved_at"])
    agents = pd.read_csv(f"{RAW}/agents.csv", parse_dates=["from_date", "to_date"])
    return t, agents


def attach_agent_roster(t, agents):
    """Join the roster row that was valid on the ticket date (agents have several rows)."""
    t = t.copy()
    t["_row"] = range(len(t))
    m = t[["_row", "agent_id", "created_at"]].merge(agents, on="agent_id", how="left")
    to_date = m["to_date"].fillna(pd.Timestamp("2100-01-01"))
    valid = (m["from_date"] <= m["created_at"]) & (m["created_at"] <= to_date)
    m = m[valid].drop_duplicates("_row")
    m = m.rename(columns={"site": "agent_site", "team": "agent_team",
                          "shift": "agent_shift", "tier": "agent_tier"})
    keep = ["_row", "agent_site", "agent_team", "agent_shift", "agent_tier"]
    t = t.merge(m[keep], on="_row", how="left").drop(columns="_row")
    return t


def run():
    os.makedirs(CLEAN, exist_ok=True)
    t, agents = load()
    log = {"raw_rows": len(t)}

    # 1. Drop stray pre-2025 rows
    t = t[t["created_at"] >= START_DATE].copy()
    log["after_dropping_pre_2025"] = len(t)

    # 2. Legacy resolved_at is UTC (policy section 9); everything else is IST
    legacy = t["source_system"] == "legacy_fd"
    t.loc[legacy, "resolved_at"] = t.loc[legacy, "resolved_at"] + IST_OFFSET

    # 3. Exact duplicates across the two systems (checked: ticket_id, customer+message,
    #    customer+sku+category with a UTC shift. Found none beyond ~1 pair of different dates,
    #    which are genuine repeat contacts, so nothing is dropped.)
    before = len(t)
    t = t.drop_duplicates("ticket_id")
    log["dupes_dropped"] = before - len(t)

    # 4. Derived fields
    t["month"] = t["created_at"].dt.to_period("M").astype(str)
    t["handle_hours"] = (t["resolved_at"] - t["first_response_at"]).dt.total_seconds() / 3600
    t["resolution_hours"] = (t["resolved_at"] - t["created_at"]).dt.total_seconds() / 3600
    t["first_response_min"] = (t["first_response_at"] - t["created_at"]).dt.total_seconds() / 60
    t["sla_target_min"] = t["channel"].map(SLA_MINUTES)
    t["sla_breach"] = t["first_response_min"] > t["sla_target_min"]
    t["hour_of_day"] = t["created_at"].dt.hour
    t["has_transfer_data"] = t["transfers"].notna()  # blank = legacy, NOT zero
    t["transferred"] = t["transfers"].gt(0).where(t["transfers"].notna())

    # 5. Roster join (agent_id only, never name)
    t = attach_agent_roster(t, agents)

    # CSAT blank stays NaN (no response). transfers blank stays NaN.
    t.to_csv(f"{CLEAN}/tickets_clean.csv", index=False)

    # Sanity checks
    neg = (t["resolution_hours"] < 0).sum()
    log["negative_resolution_after_fix"] = int(neg)
    log["no_roster_match"] = int(t["agent_shift"].isna().sum())
    log["final_rows"] = len(t)
    for k, v in log.items():
        print(f"  {k}: {v}")
    return t


if __name__ == "__main__":
    run()