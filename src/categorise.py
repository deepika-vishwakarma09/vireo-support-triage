"""Step 2: categorise tickets by what the customer wrote (customer_message only).

Pipeline (cheap by design):
  1. An LLM (Groq) labels a random training sample of tickets using prompts/<version>.txt
  2. A small TF-IDF + logistic-regression model learns from those labels
  3. The model labels every remaining ticket for free

Commands (run from the project root, venv active):
  python -m src.categorise make_sample        # create eval/sample_labels.csv to hand-check
  python -m src.categorise eval v1            # LLM accuracy of prompt v1 on the checked sample
  python -m src.categorise eval v2
  python -m src.categorise label_all v2       # full pipeline -> data/clean/tickets_labelled.csv
"""
import json
import os
import sys
import time

import pandas as pd
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline, make_union

from src.notes_rules import label_from_note
from src.taxonomy import CATEGORIES

load_dotenv()
CLEAN = "data/clean/tickets_clean.csv"
SAMPLE = "eval/sample_labels.csv"
OUT = "data/clean/tickets_labelled.csv"
BATCH = int(os.getenv("LLM_BATCH", "10"))
SLEEP = float(os.getenv("LLM_SLEEP", "2"))
TRAIN_N = int(os.getenv("TRAIN_N", "1500"))
SEED = 42


def text_of(msg):
    return str(msg).replace("\\n", " ").replace("\n", " ").strip()[:600]


# ---------------------------------------------------------------- LLM
def _client():
    from groq import Groq
    key = os.getenv("LLM_API_KEY")
    if not key:
        raise RuntimeError("LLM_API_KEY missing in .env (needed only for labels not already cached)")
    return Groq(api_key=key)


def _call_llm(system, batch, usage):
    """One request = one batch of tickets. Retries on rate limits."""
    client = _client()
    model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
    user = json.dumps([{"id": i, "text": t} for i, t in batch], ensure_ascii=False)
    for attempt in range(6):
        try:
            r = client.chat.completions.create(
                model=model, temperature=0,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}])
            usage["prompt_tokens"] += r.usage.prompt_tokens
            usage["completion_tokens"] += r.usage.completion_tokens
            usage["calls"] += 1
            data = json.loads(r.choices[0].message.content)
            return {str(x["id"]): x["category"] for x in data["labels"]}
        except Exception as e:  # rate limit, bad JSON, network
            wait = 15 * (attempt + 1)
            print(f"   retry {attempt+1}/6 after error: {str(e)[:90]} (waiting {wait}s)")
            time.sleep(wait)
    return {}


def llm_label(df, version):
    """Label df (needs ticket_id, customer_message). Results are cached on disk, so re-runs are free."""
    cache_path = f"outputs/llm_labels_{version}.csv"
    os.makedirs("outputs", exist_ok=True)
    cache = {}
    if os.path.exists(cache_path):
        c = pd.read_csv(cache_path)
        cache = dict(zip(c.ticket_id, c.label))
    todo = [(r.ticket_id, text_of(r.customer_message)) for r in df.itertuples() if r.ticket_id not in cache]
    system = open(f"prompts/{version}.txt", encoding="utf-8").read().replace(
        "{categories}", "\n".join(f"- {c}" for c in CATEGORIES))
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        got = _call_llm(system, batch, usage)
        for tid, _ in batch:
            lab = got.get(str(tid))
            cache[tid] = lab if lab in CATEGORIES else "INVALID"
        pd.DataFrame({"ticket_id": list(cache), "label": list(cache.values())}).to_csv(cache_path, index=False)
        print(f"   labelled {min(i + BATCH, len(todo))}/{len(todo)}")
        time.sleep(SLEEP)
    if usage["calls"]:
        log_path = f"outputs/token_usage_{version}.json"
        old = json.load(open(log_path)) if os.path.exists(log_path) else {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0, "tickets": 0}
        for k in usage:
            old[k] += usage[k]
        old["tickets"] += len(todo)
        json.dump(old, open(log_path, "w"), indent=2)
    return df["ticket_id"].map(cache)


# ---------------------------------------------------------------- eval sample
def make_sample(n=100):
    t = pd.read_csv(CLEAN)
    s = t.sample(n, random_state=SEED).copy()
    s["suggested_from_note"] = s["agent_notes"].map(label_from_note)
    s["gold_label"] = s["suggested_from_note"]  # YOU must check/correct every row
    cols = ["ticket_id", "channel", "category", "customer_message", "agent_notes", "suggested_from_note", "gold_label"]
    os.makedirs("eval", exist_ok=True)
    s[cols].rename(columns={"category": "bot_tag"}).to_csv(SAMPLE, index=False)
    print(f"wrote {SAMPLE}: open it in Excel, fix gold_label for every row (blank = fill it in).")
    print("Valid labels:", "; ".join(CATEGORIES))


def load_gold():
    g = pd.read_csv(SAMPLE)
    g = g[g.gold_label.isin(CATEGORIES)].copy()
    if len(g) == 0:
        raise SystemExit("No valid gold_label values in eval/sample_labels.csv. Fill them in first.")
    return g


def evaluate(version):
    g = load_gold()
    g["llm"] = llm_label(g, version).values
    acc = (g.llm == g.gold_label).mean()
    bot = (g.bot_tag == g.gold_label).mean()
    print(f"\nPrompt {version}: LLM accuracy {acc:.1%} on {len(g)} hand-checked tickets")
    print(f"Bot tag accuracy on the same tickets: {bot:.1%}")
    wrong = g[g.llm != g.gold_label]
    print("\nMost common mistakes (gold -> llm):")
    print(wrong.groupby(["gold_label", "llm"]).size().sort_values(ascending=False).head(8).to_string())
    os.makedirs("eval", exist_ok=True)
    wrong[["ticket_id", "customer_message", "gold_label", "llm"]].to_csv(f"eval/errors_{version}.csv", index=False)
    with open("eval/accuracy_report.md", "a", encoding="utf-8") as f:
        f.write(f"- prompt {version}: LLM {acc:.1%}, bot tag {bot:.1%}, n={len(g)}\n")
    return acc


# ---------------------------------------------------------------- full pipeline
def label_all(version):
    t = pd.read_csv(CLEAN)
    gold_ids = set(load_gold().ticket_id) if os.path.exists(SAMPLE) else set()
    pool = t[~t.ticket_id.isin(gold_ids)]  # keep the checked sample out of training
    train = pool.sample(min(TRAIN_N, len(pool)), random_state=SEED).copy()
    train["llm_label"] = llm_label(train, version).values
    train = train[train.llm_label.isin(CATEGORIES)]
    print(f"training classifier on {len(train)} LLM-labelled tickets")
    model = make_pipeline(
        make_union(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
                   TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=3, sublinear_tf=True)),
        LogisticRegression(max_iter=2000, C=5))
    model.fit(train.customer_message.map(text_of), train.llm_label)
    t["true_category"] = model.predict(t.customer_message.map(text_of))
    t["label_source"] = "classifier"
    lab = dict(zip(train.ticket_id, train.llm_label))
    m = t.ticket_id.isin(lab)
    t.loc[m, "true_category"] = t.loc[m, "ticket_id"].map(lab)
    t.loc[m, "label_source"] = "llm"
    t.to_csv(OUT, index=False)
    print(f"wrote {OUT}")
    if gold_ids:
        g = load_gold()
        pred = model.predict(g.customer_message.map(text_of))
        print(f"END-TO-END accuracy (classifier on unseen hand-checked sample): {(pred == g.gold_label).mean():.1%} on {len(g)}")
    return t


def run():
    version = os.getenv("PROMPT_VERSION", "v2")
    return label_all(version)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "label_all"
    ver = sys.argv[2] if len(sys.argv) > 2 else "v2"
    {"make_sample": lambda: make_sample(), "eval": lambda: evaluate(ver), "label_all": lambda: label_all(ver)}[cmd]()
