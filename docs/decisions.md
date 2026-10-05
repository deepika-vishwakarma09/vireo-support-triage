# Decisions: what was unclear, what I decided, why

1. **Tickets before Jan 2025 dropped (139 rows).** README says data starts Jan 2025. These rows are all tagged Billing and all from the legacy system, so they look like a stray extract. Keeping them lifts Billing from 20.8% to 21.8%, which is the "22%" in Priya's email.
2. **Legacy `resolved_at` shifted +5:30 (UTC to IST)**, per support-policy section 9. Before the fix 2,379 tickets resolved before they were created. After it: 0 negative, and legacy vs helpdesk mean resolution time is 26.2h vs 26.0h. I assumed `first_response_at` on legacy rows was already IST (policy only says resolution was rebuilt from UTC).
3. **Refund amounts not converted.** Policy says the legacy tool used a native unit. I compared refund to order value for both systems: ratio about 1.0 in both, so nothing to convert.
4. **No duplicates removed.** Checked ticket_id, customer + message, and customer + SKU + category with a 5:30 offset. None found beyond a pair of identical short messages nine months apart, which I treated as separate contacts.
5. **`transfers` blank = unknown, not zero.** The transfer findings use helpdesk rows only (10 months) and are scaled to a quarter.
6. **CSAT blank = no response**, excluded (CSAT not used in the final analysis).
7. **Used `agent_id`, never names.** Roster joined by date (an agent can have several rows).
8. **Category set.** 12 labels. "Order Change & Cancellation" added because it was hiding in "Other". The bot's "Other" bucket held cancellations, address changes, delivery issues and wrong-item tickets.
9. **Label rules chosen on the ROOT problem, not the customer's ask:**
   - paid but order exists and has not arrived: Delivery & Shipping
   - paid but no order was ever created: Billing & Payments
   - wrong item / wrong colour / damaged on arrival: Delivery & Shipping (no separate fulfilment label)
   - any pickup problem: Returns & Refunds
   - sound that stutters with distance or phone position: Connectivity
10. **The tool reads `customer_message` only.** Agent notes do not exist when a ticket is created, so they were used only to help build the answer key.
11. **Order Change & Cancellation counted as Logistics work** for the "true owner" view. Not stated in the policy. Sensitivity shown (Logistics 50 vs 42 per agent per month).
12. **"By team" chart is circular.** In this data, the assigned team is a direct function of the bot's tag (Billing tag always goes to Billing, and so on). So I added a chart by the team that actually resolved the ticket, which does not depend on the bot.
13. **Priya's question answered with per-agent load, not raw volume.** Teams have different sizes (Billing 4 agents, Chat 15). Tier 2 excluded per policy section 6.
14. **Stopped tuning prompts after v3.** v3 reached 98% on the 100 tickets I tuned on but 90% on 50 fresh tickets, the same as v2. I report 90%.
15. **Looked at and left out:** SLA credits (about Rs 75,000 a quarter; misses ran from 6% to 17% by hour, 6% to 13% by channel and 9% to 13% by shift, with no single hour, channel or shift standing out enough to point to one fix); bad manufacturing lot (1,267 lots, median 8 orders each, too few to trust); refund + replacement (2 tickets).
