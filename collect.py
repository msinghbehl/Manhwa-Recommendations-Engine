# collect.py
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tqdm import tqdm
import argparse

from config import (
    SUBREDDITS, QUERY_TERMS, DEFAULT_DAYS,
    POSTS_PATH, COMMENTS_PATH, RAW_DIR
)
from reddit_client import get_reddit, search_posts, fetch_comments

MAX_WORKERS = 5  # conservative; stays under Reddit's ~60 req/min rate limit


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def run_collection(days: int, post_limit: int = 60, comment_limit: int = 40):
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Collecting raw data for {days} day window into {RAW_DIR}")
    reddit = get_reddit()
    all_posts = {}
    total_comments = 0
    skipped = 0

    # 1) posts
    for sub in SUBREDDITS:
        for query in QUERY_TERMS:
            posts = search_posts(sub, query, days, limit=post_limit, reddit=reddit)
            for p in posts:
                if not p["id"]:
                    continue
                all_posts.setdefault(p["id"], p)
            time.sleep(0.2)  # tiny politeness delay (optional)

    posts_list = list(all_posts.values())
    print(f"[INFO] Unique posts collected: {len(posts_list)}")
    write_jsonl(POSTS_PATH, posts_list)

    # 2) comments — parallel fetch, batch write
    all_comments = []

    def _fetch_one(post):
        return fetch_comments(post["id"], limit=comment_limit, reddit=reddit)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_fetch_one, post): post for post in posts_list}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Fetching comments"):
            cmts = future.result()
            if cmts:
                all_comments.extend(cmts)
                total_comments += len(cmts)
            else:
                skipped += 1

    write_jsonl(COMMENTS_PATH, all_comments)

    print(
        f"[SUMMARY] Posts: {len(posts_list)} | Comments: {total_comments} | Posts with 0 comments fetched: {skipped}")
    print(f"[OUTPUT] Posts file: {POSTS_PATH}")
    print(f"[OUTPUT] Comments file: {COMMENTS_PATH}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Collect raw Reddit posts & comments (OAuth/PRAW)")
    ap.add_argument("-d", "--days", type=int,
                    default=DEFAULT_DAYS, help="Lookback window (approx)")
    ap.add_argument("--post-limit", type=int, default=60)
    ap.add_argument("--comment-limit", type=int, default=40)
    args = ap.parse_args()
    run_collection(args.days, post_limit=args.post_limit,
                   comment_limit=args.comment_limit)
