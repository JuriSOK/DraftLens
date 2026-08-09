"""Polite HTTP access for public data sources.

Every DraftLens source is public and unauthenticated. This module never sends
credentials, never bypasses rate limits, and identifies itself honestly.
"""

import json
import time
import urllib.error
import urllib.request

USER_AGENT = "DraftLens/0.1 (research project; contact: project owner)"


def http_get(url, throttle=0.0, retries=3, timeout=120):
    """Fetch bytes with a descriptive UA and polite backoff on 429/5xx.

    `throttle` sleeps BEFORE each attempt so callers can hold a steady request
    rate against APIs that ask for one.
    """
    last = None
    for attempt in range(retries):
        if throttle:
            time.sleep(throttle)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(20 * (attempt + 1))
                continue
            raise
        except Exception as e:  # transient network
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"GET failed after {retries} attempts: {url} ({last})")


def http_json(url, throttle=0.0):
    return json.loads(http_get(url, throttle=throttle).decode("utf-8"))
