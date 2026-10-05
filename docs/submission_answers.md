**Q1. What did you build, and what business outcome does it move? State the number and the money.**

**Answer:**
A tool that reads each ticket's opening message, puts it in one of 12 categories, and shows monthly volume by category and by team, plus tickets per agent per month. It found that the intake bot sends "paid but not delivered" tickets to Billing: Billing tickets are handed on 0.41 times per ticket against 0.11 for every other team, and 29% of tickets routed to Billing were resolved by Logistics agents. The goal is to bring Billing hand-offs from 0.41 to 0.11 per ticket, worth about Rs 42,000 a quarter (139 avoidable hand-offs x Rs 305). The bigger decision is where the two hires (Rs 9 lakh a year) go: Logistics is the busiest team (42 to 50 tickets per agent per month vs 32 in Billing), so they should go there, not to Billing.

---

**Q2. What does one run cost, and what would a month cost at Vireo's volume (roughly 650 tickets a week)? Show the arithmetic. If you used no paid calls, say so.**

**Answer:**
Actual spend was Rs 0. I used the Groq free tier (model openai/gpt-oss-20b) and made no paid calls. If it were paid, at list price $0.075 per 1M input tokens and $0.30 per 1M output tokens: on 100 tickets with prompt v2 the tool used 10,731 input and 8,057 output tokens, which is $0.00080 + $0.00242 = $0.0032 per 100 tickets, or about $0.000032 per ticket. The v3 prompt is a bit longer, so it costs slightly more. At 650 tickets a week, a month is 650 x 52 / 12 = about 2,817 tickets, and 2,817 x $0.000032 = about $0.09, roughly Rs 8 a month (assuming Rs 88 per dollar). The shipped design costs even less: the model labels only 600 tickets once, and a small local classifier labels everything else for free.

---

**Q3. How do you know it works? Sample size, how you checked, error rate, and the kind of case it gets wrong.**

**Answer:**
I used 150 hand-checked tickets in two sets. A 100-ticket set was used while building the prompts, and a separate 50-ticket set was kept untouched for the final test. For the first 100, Claude told me which labels were wrong or empty and I corrected 12 and filled 13. The 50 fresh tickets were first labelled by Claude and I then checked all 50 by hand. On the fresh 50, the model prompt and the final classifier both score 90% (with only 50 tickets the real figure could be roughly 79% to 96%). The intake bot's own tag scores 72% to 74% on the same tickets. Prompt v1 scored 74%, v2 90%, and v3 98% on the 100 I tuned on but only 90% on the fresh 50, so I report 90%. The mistakes are mostly "paid but the order was never created" vs "paid but not delivered" (Billing vs Delivery), and pickup problems (Returns vs Delivery).

---

**Q4. Did you change, narrow, or push back on the client's ask? What, when, and why.**

**Answer:**
Yes. Priya asked for a chart by category and by team, and for the hires to go to the biggest team, expecting Billing. (a) The "by team" chart is circular here because the team is set directly by the bot's tag, so I added a chart by the team that actually resolved each ticket. (b) After the tool labelled the messages, 39% of Billing's queue was not billing, so I pushed back on Billing and recommended Logistics. (c) I compared teams per agent rather than by raw volume, since team sizes differ (Billing has 4 agents, Chat has 15). (d) I dropped 139 stray 2024 tickets, all Billing-tagged and outside the date range; they are why her number is 22% rather than 20.8%.

---

**Q5. What is wrong with what you are handing us? Be specific: bugs, shortcuts, things you know are off.**

**Answer:**
Accuracy is measured on only 50 fresh tickets, so the real figure could be 79% to 96%. The classifier learned from 599 labels that are themselves about 90% right. The answer key was partly pre-filled by simple rules, and some labels are judgment calls (wrong item, damaged, payments with no order). The per-agent figures count tickets, not effort, and there is no handle-time data. I assumed order cancellations are Logistics work, which the policy does not say. The transfer finding uses only 10 months of data because legacy rows are blank, then scales to a quarter. v3's 98% is inflated because I tuned on those tickets. The raw data is not in the repo, there are no automated tests, and I went over the 5 hour cap.

---

**Q6. What did you deliberately leave out, and why that rather than something else?**

**Answer:**
SLA credits (about Rs 75,000 a quarter, but no single hour, channel or shift stood out enough to point to one fix); a bad manufacturing lot (1,267 lots with a median of 8 orders each, too few to trust); refund plus replacement cases (only 2); the 30-day repeat-contact cost; CSAT; handle time and Tier 2 analysis; and a dashboard. I put the time into the routing finding because it decides where Rs 9 lakh goes.

---

**Q7. Anything you built or found that nobody asked for?**

**Answer:**
The 139 stray 2024 rows that make Billing look like 22%. The "by team" view being circular. Legacy timestamps stored in UTC (2,379 tickets showed as resolved before they were created until I fixed it). A demand surge from August 2025 (orders up about 80%, tickets about doubled, tickets per 100 orders flat) while headcount stayed at 44. Pulse 2 earbuds being about 29% of all tickets, which I did not investigate further.

---

**Q8. What did you use AI for? Which tools and models, where they helped, where they wasted your time, what you threw away. Link your three-minute screen recording here.**

**Answer:**
I used Claude (chat) for planning, exploring the data, writing the pipeline code, drafting the prompts, drafting the memo, and reviewing my answer-key labels. I used Groq with openai/gpt-oss-20b (free tier) inside the tool to label tickets. It helped most in finding the Billing misrouting and the timezone bug, and in writing code quickly. It wasted time when the first answer key, built by simple rules from agent notes, had 12 wrong labels out of 87 and 13 empty ones, when the first note rules treated "firmware" as the problem when it was only the fix, and when the free-tier token limits slowed the runs and forced me to cut the training sample from 1,500 to 600 tickets. I threw away the 98% claim for prompt v3, keyword rules as the main classifier, and the first keyword estimate of how much of Billing is misrouted.

---

**Your Public Google Drive Link:**
[PUBLIC GOOGLE DRIVE LINK]

---

**Q9. Someone picks this up on Monday and you are unreachable. The three things they need to know.**

**Answer:**
(1) Put the five client CSVs in `data/raw/` and run `python run.py`; the model labels are cached, so no API key is needed. (2) Do not tune prompts on `eval/test_labels.csv`; it is the untouched set and gives the honest accuracy of about 90%. (3) Before signing the hires, check handle time per ticket and the assumption that order cancellations are Logistics work, because the per-agent figures count tickets, not effort.

---

**Q10. Honest hours spent. One number.**

**Answer:**
  8

---

**Github Repo Link**

https://github.com/deepika-vishwakarma09/vireo-support-triage.git
