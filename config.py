# config.py
import datetime
import logging
import os
from pathlib import Path

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

# User-Agent (IMPORTANT for Reddit — set USER_AGENT in .env to a real email)
USER_AGENT = os.getenv(
    "USER_AGENT", "ManhwaMultiRecBot/0.1 (contact: you@example.com)")

# Data paths
TODAY = datetime.date.today().isoformat()
DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw" / TODAY
LOG_DIR = DATA_DIR / "logs"

POSTS_PATH = RAW_DIR / "posts.jsonl"
COMMENTS_PATH = RAW_DIR / "comments.jsonl"
LOG_PATH = LOG_DIR / f"run_{TODAY}.log"

# Networking / politeness
REQUEST_TIMEOUT = 10
MAX_COMMENT_RETRIES = 3
BASE_URL = "https://www.reddit.com"

# ---------------------------------------------------------------------------
# Logging — StreamHandler only at import time; FileHandler added by init_dirs()
# ---------------------------------------------------------------------------
# WARNING: Never change level to logging.DEBUG in production.
# PRAW logs full OAuth token exchange bodies at DEBUG level,
# which would write your Reddit credentials to the log file.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


def init_dirs() -> None:
    """Create required data directories and wire up the log file handler."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    # Add file handler now that LOG_DIR exists
    file_handler = logging.FileHandler(LOG_PATH)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logging.getLogger().addHandler(file_handler)
