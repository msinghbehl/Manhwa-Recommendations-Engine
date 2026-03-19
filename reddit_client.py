# reddit_client.py
import os
from dotenv import load_dotenv
import praw
from praw.models import Comment

load_dotenv()


def get_reddit() -> praw.Reddit:
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD"),
        user_agent=os.getenv("USER_AGENT", "ManhwaRecBot/1.0")
    )


def search_posts(sub: str, query: str, days: int, limit: int = 60, reddit: praw.Reddit | None = None) -> list[dict]:
    """Return posts that match a query inside a subreddit for a given time window."""
    if reddit is None:
        reddit = get_reddit()
    time_filter = "day" if days <= 1 else "week" if days <= 7 else "month" if days <= 31 else "year"
    subreddit = reddit.subreddit(sub)

    posts = []
    for s in subreddit.search(query, sort="new", time_filter=time_filter, limit=limit):
        posts.append({
            "id": s.id,
            "subreddit": sub,
            "query_term": query,
            "title": s.title,
            "created_utc": s.created_utc,
            "permalink": s.permalink,
            "num_comments": s.num_comments,
            "author": str(s.author),
            "score": s.score,
        })
    return posts


def fetch_comments(post_id: str, limit: int = 40, reddit: praw.Reddit | None = None) -> list[dict]:
    """Fetch up-to-`limit` comments from a submission (flattened)."""
    if reddit is None:
        reddit = get_reddit()
    subm = reddit.submission(id=post_id)
    # fully expand, still cheap enough for small runs
    subm.comments.replace_more(limit=0)
    comments = []
    for c in subm.comments.list()[:limit]:
        if not isinstance(c, Comment):
            continue
        comments.append({
            "comment_id": c.id,
            "post_id": post_id,
            "body": c.body or "",
            "author": str(c.author),
            "created_utc": c.created_utc,
            "score": c.score,
            "permalink": c.permalink,
            "subreddit": subm.subreddit.display_name,
        })
    return comments
