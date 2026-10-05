# AI usage log

I used two AI tools. This is what I used them for, in order, and where they helped or didn't.

## Tools
- **Claude** (claude.ai chat): the main helper from start to end.
- **Groq API, model `openai/gpt-oss-20b`**: only inside the tool, to label tickets. Free tier.

## What I used Claude for
Claude was my main helper. I used it to plan the steps, to look through the data together, to write the code, to draft the prompts, and to draft the docs. Some of the findings (the timezone problem, the stray 2024 rows, Billing tickets that are really delivery problems) came out of working through the data with it.

## What I did myself
- Made the repo, virtual env and Groq key, and ran every command.
- Fixed the answer key for the first 100 test tickets. Claude read every row and told me which labels were wrong or empty. I made those changes: 12 wrong labels corrected and 13 empty ones filled.
- The 50 fresh test tickets were first labelled by Claude, before I ran prompt v3. I then checked all 50 by hand myself.
- Picked the model after looking at the Groq models page.
- Read the results and decided to stop changing the prompt after v3.

## Where it helped
- Finding the Billing problem quickly. By hand this would have taken me much longer.
- The prompt jump from v1 (74%) to v2 (90%).
- Catching that v3's 98% was not real because I tuned it on the same tickets I tested on.

## Where it wasted time or was wrong
- The first answer key was made by simple rules from agent notes. When I checked it, 12 of 87 labels were wrong and 13 were empty. I had to go through it again.
- The first note rules marked "firmware" as the problem when it was only the fix the agent tried. It needed rewriting.
- Prompt v1 gave 10 answers that were not valid categories.
- v3 looked great (98%) but gave no gain on new tickets (90%, same as v2).
- Groq free limits are small, so runs were slow and I had to lower the number of tickets sent to the model from 1,500 to 600.

## What I threw away
- The 98% claim for prompt v3.
- Keyword rules as the main classifier. They are only used to pre-fill the answer key.
- A first quick estimate of how much of Billing is misrouted (from keywords). I replaced it with the classifier's 39% and the roster check (29%).
- Looking for a bad manufacturing lot, and the SLA-credit idea. Not enough signal, so I left them out.

## Cost
- Groq: Rs 0 (free tier).
- Claude: (free plan)
