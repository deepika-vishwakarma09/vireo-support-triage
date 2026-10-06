# Vireo Audio: Support Ticket Triage

Reads every support ticket's opening message, assigns one of 12 categories, and shows where the work really lands: monthly volume by category and by team, and tickets per agent per month.

**Main finding:** the intake bot sends "paid but not delivered" tickets to Billing. About 39% of Billing's queue is not a billing issue, and 29% of it was resolved by Logistics agents. Corrected for this, Logistics is the busiest team (about 42 to 50 tickets per agent per month in the last six months, vs 32 for Billing). Recommendation: put the two hires in Logistics and fix the routing. Full reasoning in [`docs/memo.md`](docs/memo.md).

## Run it (clean machine)

Needs Python 3.10 or newer.

```bash
git clone https://github.com/deepika-vishwakarma09/vireo-support-triage.git
cd vireo-support-triage
python -m venv venv
.\venv\Scripts\Activate.ps1          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```

## Input data

The five client-provided CSVs are intentionally excluded from this repository
because they contain customer/support data.

Before running the pipeline, place these files in `data/raw/`:

- tickets.csv
- agents.csv
- orders.csv
- customers.csv
- products.csv

```bash
python run.py
```

**No API key is needed.** The LLM labels are cached in `outputs/llm_labels_v3.csv`. A key is only needed if that file is deleted or you change the prompt: copy `.env.example` to `.env` and fill in a Groq key (`LLM_MODEL=openai/gpt-oss-20b`).

Takes 2 to 3 minutes. Expected output includes:
```
final_rows: 11641
negative_resolution_after_fix: 0
END-TO-END accuracy ... on sample_labels.csv: 93.0% on 100
END-TO-END accuracy ... on test_labels.csv: 90.0% on 50
Billing queue (2425 tickets, 20.8% of all): classifier says 39% are NOT billing issues.
Label-free check: 29% of tickets routed to Billing were resolved by a Logistics agent.
```
Results land in `outputs/` (tables, `findings.txt`) and `outputs/charts/` (5 PNG charts).

## How it works

1. **Clean** (`src/clean.py`): drops 139 stray 2024 rows, fixes legacy UTC timestamps, joins the agent roster by date.
2. **Categorise** (`src/categorise.py`): an LLM (Groq, `gpt-oss-20b`) labels 600 random tickets from the customer's message using `prompts/v3.txt`. A small TF-IDF + logistic regression model learns from those and labels the other ~11,000 for free.
3. **Analyse** (`src/analyse.py`): compares teams three ways: assigned by the bot, resolved by whom, and true owner by category. Also measures hand-offs and their cost.
4. **Charts** (`src/charts.py`).

## How I know it works

| | Tuned-on set (100 tickets) | Fresh set (50 tickets) |
|---|---|---|
| Intake bot's own tag | 72% | 74% |
| Prompt v1 | 74% | n/a |
| Prompt v2 | 90% | 90% |
| Prompt v3 | 98% (inflated, tuned on these) | 90% |
| Final classifier (what the pipeline uses) | 93% | 90% |

Sets are in `eval/`. Only 50 fresh tickets were checked, so the true figure is likely 79% to 96%. See `prompts/CHANGELOG.md` for what changed between versions. Re-run an evaluation with `python -m src.categorise eval v3 test`.

## Folder map

```
run.py                one command, whole pipeline
src/                  clean, categorise, analyse, charts, label set, note rules
prompts/              v1, v2, v3 and CHANGELOG
eval/                 hand-checked labels (dev set and held-out set) and error lists
outputs/              tables, findings.txt, charts/, cached LLM labels, token usage
docs/                 memo, decisions, handoff notes, AI usage log
```

## Main outputs

After a successful run:

- `outputs/findings.txt` — key business findings
- `outputs/team_load.csv` — team workload
- `outputs/monthly_by_bot_category.csv` — monthly category volume
- `outputs/monthly_by_resolving_team.csv` — monthly resolving-team volume
- `outputs/charts/` — generated charts

## Read next

- [`docs/decisions.md`](docs/decisions.md): what was unclear, what I decided and why
- [`docs/handoff_notes.md`](docs/handoff_notes.md): what to know and known shortcuts
- [`docs/memo.md`](docs/memo.md): the one-page memo to Priya Raman
