# reddit_client.py
import os
import praw
from praw.models import Comment


def get_reddit() -> praw.Reddit:
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    username = os.environ.get("REDDIT_USERNAME")
    password = os.environ.get("REDDIT_PASSWORD")
    user_agent = os.environ.get("USER_AGENT", "ManhwaRecBot/1.0")

    missing = [k for k, v in {
        "REDDIT_CLIENT_ID": client_id,
        "REDDIT_CLIENT_SECRET": client_secret,
        "REDDIT_USERNAME": username,
        "REDDIT_PASSWORD": password,
    }.items() if not v]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Check your .env file."
        )

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        username=username,
        password=password,
        user_agent=user_agent,
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
