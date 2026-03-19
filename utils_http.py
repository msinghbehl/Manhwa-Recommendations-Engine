# utils_http.py
import time
import sys
import json
import random
import requests
from typing import Optional
from config import USER_AGENT, REQUEST_TIMEOUT

HEADERS = {"User-Agent": USER_AGENT}


def get_json(url: str, params: dict, max_retries: int = 3, base_sleep: float = 1.0) -> Optional[dict]:
    """
    GET JSON with polite exponential backoff.
    Returns dict or None if ultimately failed / non-JSON.
    """
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params,
                                headers=HEADERS, timeout=REQUEST_TIMEOUT)
            status = resp.status_code

            if status == 429:  # rate limit
                wait = base_sleep * (1.5 ** attempt) + random.uniform(0, 0.5)
                print(
                    f"[WARN] 429 rate limit. Sleeping {wait:.1f}s", file=sys.stderr)
                time.sleep(wait)
                continue

            resp.raise_for_status()

            if "application/json" not in resp.headers.get("content-type", ""):
                raise ValueError("Non-JSON content-type")

            return resp.json()

        except (requests.RequestException, ValueError, json.JSONDecodeError) as e:
            wait = base_sleep * (1.5 ** attempt) + random.uniform(0, 0.5)
            print(
                f"[WARN] Attempt {attempt} failed ({e}). Sleeping {wait:.1f}s", file=sys.stderr)
            time.sleep(wait)

    print(f"[ERROR] Giving up on {url}", file=sys.stderr)
    return None
