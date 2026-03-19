# config.py
from pathlib import Path
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Subreddits we will scan (expand later)
SUBREDDITS = [
    "manhwa",
    "manhwarecommendations",
    "webtoons"
]

# Query terms capturing recommendation intent
QUERY_TERMS = [
    "recommend",
    "suggest",
    "looking for",
    "underrated",
    "must read"
]

# Default lookback window in days
DEFAULT_DAYS = int(os.getenv("LOOKBACK_DAYS", "7"))

# User-Agent (IMPORTANT for Reddit)
USER_AGENT = os.getenv(
    "USER_AGENT", "ManhwaMultiRecBot/0.1 (contact: you@example.com)")

# Data paths
TODAY = datetime.date.today().isoformat()
DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw" / TODAY
LOG_DIR = DATA_DIR / "logs"

RAW_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

POSTS_PATH = RAW_DIR / "posts.jsonl"
COMMENTS_PATH = RAW_DIR / "comments.jsonl"
LOG_PATH = LOG_DIR / f"run_{TODAY}.log"

# Networking / politeness
REQUEST_TIMEOUT = 10
MAX_COMMENT_RETRIES = 3
BASE_URL = "https://www.reddit.com"
