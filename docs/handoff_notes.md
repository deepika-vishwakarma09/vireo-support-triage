# Handoff: the three things Monday's person must know

1. **Run it:** put the five client CSVs (tickets, agents, orders, customers, products) in `data/raw/`, then `python run.py`. They are not in the repo because they hold customer data. LLM labels are cached in `outputs/llm_labels_v3.csv`, so no API key is needed unless that cache is deleted. Settings sit in `.env.example`.
2. **Never tune on the test set.** `eval/sample_labels.csv` (100) was used to build prompts v2 and v3. `eval/test_labels.csv` (50) was kept fresh and gives the honest figure, about 90%. If the data or the categories change, re-label a new fresh set.
3. **The recommendation rests on two assumptions to verify before Rs 9 lakh is signed:** (a) per-agent figures count tickets, not effort, so get handle time per ticket from Sameer; (b) cancellations and address changes were counted as Logistics work.

## Known bugs and shortcuts
- Classifier trained on 599 labels that are themselves about 90% right. Real accuracy has a wide range (79% to 96%) because only 50 fresh tickets were checked.
- Answer-key labels were pre-filled by simple rules from agent notes, then checked row by row with Claude's help and corrected. Some are judgment calls (wrong item, damaged, no-order payments).
- Transfer finding uses only 10 months (helpdesk); legacy rows are blank.
- Average agents per team comes from the roster by month; leave and absences are not in the data.
- No automated tests. `make_sample` refuses to overwrite an existing labels file.
