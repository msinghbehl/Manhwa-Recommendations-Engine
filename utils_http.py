# utils_http.py
import json
import logging
import random
import time
from urllib.parse import urlparse

import requests

from config import USER_AGENT, REQUEST_TIMEOUT

HEADERS = {"User-Agent": USER_AGENT}

# Allowlist of permitted hosts — prevents SSRF if a URL ever comes from external data
_ALLOWED_HOSTS = {"www.reddit.com", "oauth.reddit.com", "api.reddit.com"}


def get_json(url: str, params: dict, max_retries: int = 3, base_sleep: float = 1.0) -> dict | None:
    """
    GET JSON with polite exponential backoff.
    Returns dict or None if ultimately failed / non-JSON.
    """
    parsed = urlparse(url)
    if parsed.hostname not in _ALLOWED_HOSTS:
        logging.error("Blocked request to disallowed host: %s", parsed.hostname)
        return None

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params,
                                headers=HEADERS, timeout=REQUEST_TIMEOUT)
            status = resp.status_code

            if status == 429:  # rate limit
                wait = base_sleep * (1.5 ** attempt) + random.uniform(0, 0.5)  # nosec B311
                logging.warning("429 rate limit. Sleeping %.1fs", wait)
                time.sleep(wait)
                continue

            resp.raise_for_status()

            if "application/json" not in resp.headers.get("content-type", ""):
                raise ValueError("Non-JSON content-type")

            return resp.json()

        except (requests.RequestException, ValueError, json.JSONDecodeError) as e:
            wait = base_sleep * (1.5 ** attempt) + random.uniform(0, 0.5)  # nosec B311
            logging.warning("Attempt %d failed (%s). Sleeping %.1fs", attempt, e, wait)
            time.sleep(wait)

    logging.error("Giving up on %s", url)
    return None
