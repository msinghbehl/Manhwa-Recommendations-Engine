# extract.py
import json
import math
import os
import re
import string
import datetime
import argparse
from pathlib import Path
from collections import defaultdict
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

DECAY_BASE = 0.9  # per-day recency decay: 0.9^7 ≈ 0.48, 0.9^28 ≈ 0.05

RAW_ROOT = Path("data/raw")
BLACKLIST_PATH = Path("data/blacklist.txt")
WHITELIST_PATH = Path("data/whitelist.txt")

LIST_PREFIX = re.compile(r"^[\-\*\•\d\)\(]+\s*")
META_PREFIX = re.compile(
    r"(?i)^(best|plan|s\s*tier|finished|completed|ongoing|dropped|status|genre|rating|score)[:\-\s]+")
CHAPTER_RE = re.compile(r"^ch(?:apter)?\s*\d+", re.I)
MARK_RE = re.compile(r"(?:\*\*|\*|['\"“”])([^'\n\*]{2,90})(?:\*\*|\*|['\"“”])")


def load_list(path: Path) -> set:
    if not path.exists():
        return set()
    return {l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()}


def parse_args():
    ap = argparse.ArgumentParser(
        description="Extract manhwa titles from raw Reddit comments")
    ap.add_argument(
        "--date", help="YYYY-MM-DD folder under data/raw to process (default: latest)")
    return ap.parse_args()


def get_latest_date_dir() -> str:
    dated = [p for p in RAW_ROOT.iterdir() if p.is_dir()]
    if not dated:
        raise SystemExit("No folders under data/raw/. Run collect.py first.")
    return max(dated, key=lambda p: p.stat().st_mtime).name


def read_jsonl(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def extract_candidates(text: str, whitelist: set, blacklist: set):
    cands = set()
    for raw in MARK_RE.findall(text):
        cleaned = clean_candidate(raw, whitelist, blacklist)
        if cleaned:
            cands.add(cleaned)
    for line in text.splitlines():
        line = LIST_PREFIX.sub("", line).strip()
        line = META_PREFIX.sub("", line).strip()
        if not line:
            continue
        cleaned = clean_candidate(line, whitelist, blacklist)
        if cleaned:
            cands.add(cleaned)
    return cands


URL_RE = re.compile(r"https?://", re.I)
EMOJI_RE = re.compile(r"^[\W_]+$")


def clean_candidate(text: str, whitelist: set, blacklist: set) -> str | None:
    text = text.strip(string.punctuation + " \u200b")

    text = text.strip(string.punctuation + " \u200b")
    if not text or URL_RE.search(text):
        return None
    if EMOJI_RE.match(text):          # all emoji / symbols
        return None
    if re.search(r"(?i)\bremind\s*me\b", text):
        return None
    if not text:
        return None
    if text in whitelist:
        return text
    if text.lower() in blacklist:
        return None
    if CHAPTER_RE.match(text):
        return None

    words = text.split()
    if not (1 <= len(words) <= 8):
        return None
    if len(words) > 1 and all(w.islower() for w in words):
        return None

    cap_words = sum(1 for w in words if w and (
        w[0].isupper() or w[0].isdigit()))
    if len(words) > 1 and cap_words / len(words) < 0.4:
        return None

    lower_words = {w.lower() for w in words}
    if lower_words & {"comment", "tier", "plan", "read", "chapter"}:
        return None

    return " ".join(words)


def canon_key(t: str) -> str:
    t2 = re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()
    parts = t2.split()
    if parts and parts[0] in {"the", "a", "an"}:
        parts = parts[1:]
    return "".join(parts)


def fuzzy_merge(rows: pd.DataFrame, threshold: int = 92) -> pd.DataFrame:
    try:
        from rapidfuzz import fuzz
    except ImportError:
        return rows
    used = set()
    out = []
    titles = list(rows["title"])
    for i, t in enumerate(titles):
        if i in used:
            continue
        idxs = [i]
        for j in range(i + 1, len(titles)):
            if j in used:
                continue
            if fuzz.token_sort_ratio(titles[i].lower(), titles[j].lower()) >= threshold:
                idxs.append(j)
                used.add(j)
        sub = rows.iloc[idxs]
        rep = max(sub["title"], key=len)
        out.append({
            "title": rep,
            "mentions": sub["mentions"].sum(),
            "unique_commenters": sub["unique_commenters"].sum(),
            "subreddit_count": sub["subreddit_count"].sum()
        })
    return pd.DataFrame(out)


def main():
    args = parse_args()
    raw_date = args.date or get_latest_date_dir()
    raw_dir = RAW_ROOT / raw_date
    comments_path = raw_dir / "comments.jsonl"
    processed_dir = Path("data/processed") / raw_date
    processed_dir.mkdir(parents=True, exist_ok=True)

    if not comments_path.exists():
        raise SystemExit(f"Comments file not found: {comments_path}")

    blacklist = {w.lower() for w in load_list(BLACKLIST_PATH)}
    whitelist = load_list(WHITELIST_PATH)

    # Load post scores for quality weighting
    posts_path = raw_dir / "posts.jsonl"
    post_score_lookup = {}
    if posts_path.exists():
        for prow in read_jsonl(posts_path):
            pid = prow.get("id")
            if pid:
                post_score_lookup[pid] = max(0, prow.get("score", 0))

    counts = defaultdict(float)
    commenters = defaultdict(set)
    subs = defaultdict(set)
    snippets = defaultdict(list)  # canon_key → comment bodies (for AI validation)

    total_comments = total_cands = total_kept = 0
    now_ts = datetime.datetime.utcnow().timestamp()

    for row in read_jsonl(comments_path):
        total_comments += 1
        body = row.get("body") or ""
        author = row.get("author") or "unknown"
        subreddit = row.get("subreddit") or "unknown"

        # Per-mention weight: recency decay × post quality
        days_old = max(0, (now_ts - (row.get("created_utc") or now_ts)) / 86400)
        decay = DECAY_BASE ** days_old
        post_score = post_score_lookup.get(row.get("post_id"), 0)
        post_weight = math.log1p(post_score) if post_score > 0 else 1.0
        mention_weight = decay * post_weight

        titles = extract_candidates(body, whitelist, blacklist)
        total_cands += len(titles)
        unique_titles = set(titles)
        total_kept += len(unique_titles)

        for t in unique_titles:
            counts[t] += mention_weight
            commenters[t].add(author)
            subs[t].add(subreddit)
            # Store up to 3 comment snippets per canonical key for AI validation
            ck = canon_key(t)
            if len(snippets[ck]) < 3:
                snippets[ck].append(body[:300])

    # raw counts
    df = pd.DataFrame({
        "title": list(counts.keys()),
        "mentions": list(counts.values()),
        "unique_commenters": [len(commenters[t]) for t in counts],
        "subreddit_count": [len(subs[t]) for t in counts],
    }).sort_values("mentions", ascending=False)

    raw_csv = processed_dir / "raw_counts.csv"
    df.to_csv(raw_csv, index=False)
    print(df.head(20).to_string(index=False))
    print(f"\nSaved → {raw_csv}")

    # ----- CLEAN & MERGE -----
    # 1) first-pass by canonical key (blacklist already filtered in clean_candidate)
    df["ckey"] = df["title"].apply(canon_key)
    g = (df.groupby("ckey")
         .agg({
             "title": lambda s: max(s, key=len),
             "mentions": "sum",
             "unique_commenters": "sum",
             "subreddit_count": "sum"
         })
         .reset_index(drop=True))

    # 3) optional fuzzy merge
    clean = fuzzy_merge(g, threshold=88)

    # 4) simple score
    clean["score"] = (clean["mentions"]
                      + 0.5 * clean["unique_commenters"]
                      + 1.2 * clean["subreddit_count"])
    clean = clean.sort_values("score", ascending=False).reset_index(drop=True)

    # 5) optional AI sentiment validation (runs only if ANTHROPIC_API_KEY is set)
    if os.getenv("ANTHROPIC_API_KEY"):
        from validate import ai_validate
        print(f"\n[AI] Validating top {min(150, len(clean))} candidates with Claude...")
        candidates_with_snippets = {
            row["title"]: snippets.get(canon_key(row["title"]), [])
            for _, row in clean.iterrows()
        }
        labels = ai_validate(candidates_with_snippets)
        if labels:
            clean["ai_sentiment"] = clean["title"].map(labels).fillna("unknown")
            print(f"[AI] Labeled {len(labels)} titles — noise/negative will appear flagged in dashboard")
        else:
            print("[AI] Validation skipped or failed — no labels added")

    out_csv = processed_dir / "clean_counts.csv"
    clean.to_csv(out_csv, index=False)
    print("\nTop 20 clean:\n", clean.head(20).to_string(index=False))
    print(f"\nSaved → {out_csv}")

    print(
        f"\n[STATS] comments: {total_comments}, candidates: {total_cands}, kept(after dedup): {total_kept}")


if __name__ == "__main__":
    main()
