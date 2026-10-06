# Prompt changelog

The model only sees the customer's opening message. Every prompt asks for JSON with one category per ticket.

## Results

Dev set = 100 hand-checked tickets I looked at while building prompts. Fresh set = 50 hand-checked tickets I never tuned on (this is the honest number).

| Version | What changed | Why | Dev set (100) | Fresh set (50) |
|---|---|---|---|---|
| Bot tag (as exported) | none | the client's existing tag | 72% | 74% |
| v1 | List of categories and "classify this ticket" | Baseline | 74%, 10 invalid answers | not run |
| v2 | Choose by the root problem, not the words. Added rules and 7 examples. "Paid but not delivered" is Delivery, not Billing | v1 sent pickup tickets to Delivery and gave answers that were not real categories | 90%, 0 invalid | 90% |
| v3 | Split the "paid" rule in two (order exists, not arrived = Delivery; no order was created = Billing). Added rules for wrong or damaged items, any pickup problem, and sound that cuts with distance. Said "Other" is rare | v2 sent wrong-item tickets to Other, "paid but no order" to Delivery, and pickups to Delivery | 98% (inflated, I wrote the rules from these tickets) | 90% |
| Final classifier (what the pipeline uses) | A small TF-IDF + logistic regression model trained on 599 labels from the v3 prompt | Labels the other ~11,000 tickets for free | 93% | 90% |

Decision: I stopped tuning after v3. It gained nothing on fresh tickets, so I report 90%.

## What each version got wrong

- **v1:** return-pickup tickets labelled Delivery (6 of 100); 10 answers that were not valid categories.
- **v2:** wrong-item or damaged tickets labelled Other or Returns (4); "money deducted, no order" labelled Delivery (2); pickup tickets labelled Delivery (3); one sound-cutting ticket labelled Audio instead of Connectivity.
- **v3:** on fresh tickets, a few Delivery vs Billing mix-ups in both directions, and one ticket labelled App & Firmware that was Other.

## Thrown away

- The 98% score for v3. It was tuned on the same tickets it was tested on.
- Keyword rules as the main classifier. I only use them to pre-fill my answer key.
- My first keyword estimate of how much of Billing is misrouted. The tool's 39% replaced it.
- Training the classifier on 1,500 labelled tickets. Free-tier limits cut it to 600.
