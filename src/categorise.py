"""Step 2: categorise tickets by what the customer wrote (customer_message only).

Pipeline (cheap by design):
  1. An LLM (Groq) labels a random training sample of tickets using prompts/<version>.txt
  2. A small TF-IDF + logistic-regression model learns from those labels
  3. The model labels every remaining ticket for free

Commands (run from the project root, venv active):
  python -m src.categorise make_sample        # create eval/sample_labels.csv to hand-check (dev set, 100)
  python -m src.categorise make_sample test   # 50 fresh held-out tickets in eval/test_labels.csv
  python -m src.categorise eval v1            # LLM accuracy of prompt v1 on the checked sample
  python -m src.categorise eval v2
  python -m src.categorise eval v3 test       # score on the held-out set
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
TRAIN_N = int(os.getenv("TRAIN_N", "600"))
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
    model = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")
    user = json.dumps([{"id": i, "text": t} for i, t in batch], ensure_ascii=False)
    for attempt in range(6):
        try:
            extra = {}
            if "gpt-oss" in model:
                # gpt-oss are reasoning models: keep reasoning short so it is fast and cheap
                extra["extra_body"] = {"reasoning_effort": "low"}
            r = client.chat.completions.create(
                model=model, temperature=0, max_completion_tokens=4000,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}], **extra)
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
TEST = "eval/test_labels.csv"   # fresh held-out tickets, never used to tune prompts


def make_sample(n=100, path=SAMPLE):
    t = pd.read_csv(CLEAN)
    seed = SEED
    if path != SAMPLE and os.path.exists(SAMPLE):   # held-out set: different seed, no overlap with dev set
        t = t[~t.ticket_id.isin(pd.read_csv(SAMPLE).ticket_id)]
        seed = 7
    if os.path.exists(path):
        raise SystemExit(f"{path} already exists (it would overwrite your hand-checked labels). Delete it first if you really want a new one.")
    s = t.sample(n, random_state=seed).copy()
    s["suggested_from_note"] = s["agent_notes"].map(label_from_note)
    s["gold_label"] = s["suggested_from_note"]  # YOU must check/correct every row
    cols = ["ticket_id", "channel", "category", "customer_message", "agent_notes", "suggested_from_note", "gold_label"]
    os.makedirs("eval", exist_ok=True)
    s[cols].rename(columns={"category": "bot_tag"}).to_csv(path, index=False)
    print(f"wrote {path}: open it in Excel, fix gold_label for every row (blank = fill it in).")
    print("Valid labels:", "; ".join(CATEGORIES))


def load_gold(path=SAMPLE):
    g = pd.read_csv(path)
    g = g[g.gold_label.isin(CATEGORIES)].copy()
    if len(g) == 0:
        raise SystemExit(f"No valid gold_label values in {path}. Fill them in first.")
    return g


def evaluate(version, path=SAMPLE):
    g = load_gold(path)
    g["llm"] = llm_label(g, version).values
    acc = (g.llm == g.gold_label).mean()
    bot = (g.bot_tag == g.gold_label).mean()
    name = os.path.basename(path)
    print(f"\nPrompt {version} on {name}: LLM accuracy {acc:.1%} on {len(g)} hand-checked tickets")
    print(f"Bot tag accuracy on the same tickets: {bot:.1%}")
    wrong = g[g.llm != g.gold_label]
    print("\nMost common mistakes (gold -> llm):")
    print(wrong.groupby(["gold_label", "llm"]).size().sort_values(ascending=False).head(8).to_string())
    os.makedirs("eval", exist_ok=True)
    tag = "" if path == SAMPLE else "_test"
    wrong[["ticket_id", "customer_message", "gold_label", "llm"]].to_csv(f"eval/errors_{version}{tag}.csv", index=False)
    with open("eval/accuracy_report.md", "a", encoding="utf-8") as f:
        f.write(f"- prompt {version} on {name}: LLM {acc:.1%}, bot tag {bot:.1%}, n={len(g)}\n")
    return acc


# ---------------------------------------------------------------- full pipeline
def label_all(version):
    t = pd.read_csv(CLEAN)
    gold_ids = set()
    for pth in (SAMPLE, TEST):
        if os.path.exists(pth):
            gold_ids |= set(load_gold(pth).ticket_id)
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
        for pth in (SAMPLE, TEST):
            if os.path.exists(pth):
                g = load_gold(pth)
                pred = model.predict(g.customer_message.map(text_of))
                print(f"END-TO-END accuracy (classifier, unseen tickets) on {os.path.basename(pth)}: {(pred == g.gold_label).mean():.1%} on {len(g)}")
    return t


def run():
    version = os.getenv("PROMPT_VERSION", "v3")
    return label_all(version)


if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args[0] if args else "label_all"
    if cmd == "make_sample":      # make_sample        -> 100 dev tickets
        if len(args) > 1 and args[1] == "test":   # make_sample test   -> 50 fresh held-out tickets
            make_sample(50, TEST)
        else:
            make_sample()
    elif cmd == "eval":           # eval v3   |   eval v3 test
        ver = args[1] if len(args) > 1 else "v2"
        evaluate(ver, TEST if len(args) > 2 and args[2] == "test" else SAMPLE)
    elif cmd == "label_all":
        label_all(args[1] if len(args) > 1 else "v2")
    else:
        raise SystemExit("commands: make_sample [test] | eval <version> [test] | label_all <version>")
