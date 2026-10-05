"""Step 4: monthly charts (the deliverable Priya asked for) plus the team-load chart."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

OUT = "outputs"
CH = f"{OUT}/charts"


def stacked(csv, title, fname):
    d = pd.read_csv(f"{OUT}/{csv}", index_col=0)
    ax = d.plot(kind="bar", stacked=True, figsize=(12, 5.5), colormap="tab20", width=0.85)
    ax.set_title(title)
    ax.set_xlabel("")
    ax.set_ylabel("Tickets")
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=8, frameon=False)
    plt.xticks(rotation=60, ha="right")
    plt.tight_layout()
    plt.savefig(f"{CH}/{fname}", dpi=150)
    plt.close()


def team_load():
    d = pd.read_csv(f"{OUT}/team_load.csv", index_col=0).drop(index="Escalations & Warranty", errors="ignore")
    cols = {"assigned_per_agent_month": "Assigned by bot",
            "resolved_per_agent_month": "Actually resolved",
            "true_owner_per_agent_month": "True owner (reclassified)"}
    ax = d[list(cols)].rename(columns=cols).plot(kind="bar", figsize=(10, 5), width=0.8)
    ax.set_title("Tickets per agent per month, Tier 1 teams (higher = busier)")
    ax.set_xlabel("")
    ax.set_ylabel("Tickets per agent per month")
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(f"{CH}/team_load_per_agent.png", dpi=150)
    plt.close()


def run():
    os.makedirs(CH, exist_ok=True)
    stacked("monthly_by_bot_category.csv", "Monthly tickets by category (bot tag, as exported)", "monthly_by_category_bot.png")
    stacked("monthly_by_true_category.csv", "Monthly tickets by category (reclassified from the customer's message)", "monthly_by_category_true.png")
    stacked("monthly_by_assigned_team.csv", "Monthly tickets by team the bot routed to", "monthly_by_team_assigned.png")
    stacked("monthly_by_resolving_team.csv", "Monthly tickets by team that actually resolved them", "monthly_by_team_resolved.png")
    team_load()
    print(f"charts written to {CH}")


if __name__ == "__main__":
    run()
