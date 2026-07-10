"""A tiny on-disk HTTP-JSON cache.

Two jobs:
  1. Make the agent fast and polite to public APIs (EBI OLS, Europe PMC).
  2. Make a *fully offline* demo possible — pre-fetched responses are shipped as
     fixtures so the tool runs on an air-gapped interview laptop.

Set CLARA_CACHE to point at a fixtures directory; set CLARA_OFFLINE=1 to force
cache-only (never touch the network).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


def cache_dir() -> str:
    d = os.environ.get("CLARA_CACHE") or os.path.join(os.getcwd(), ".clara_cache")
    os.makedirs(d, exist_ok=True)
    return d


def _key(url: str, params: Dict[str, Any]) -> str:
    raw = url + "?" + urlencode(sorted((params or {}).items()))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _index_path() -> str:
    return os.path.join(cache_dir(), "_index.json")


def _record_index(key: str, url: str, params: Dict[str, Any]) -> None:
    idx_path = _index_path()
    idx = {}
    if os.path.exists(idx_path):
        try:
            with open(idx_path) as fh:
                idx = json.load(fh)
        except Exception:
            idx = {}
    idx[key] = {"url": url, "params": params}
    with open(idx_path, "w") as fh:
        json.dump(idx, fh, indent=2)


def http_get_json(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 12,
    offline: Optional[bool] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, Any]]:
    """GET url?params -> parsed JSON, cached on disk.

    Returns None on a miss when offline, or on network failure.
    """
    params = params or {}
    if offline is None:
        offline = os.environ.get("CLARA_OFFLINE", "0") == "1"

    key = _key(url, params)
    path = os.path.join(cache_dir(), key + ".json")

    if os.path.exists(path):
        try:
            with open(path) as fh:
                return json.load(fh)
        except Exception:
            pass  # fall through and re-fetch

    if offline or requests is None:
        return None

    hdrs = headers or {"User-Agent": "CLARA/0.1 (cell-ontology curation)"}
    data = None
    for attempt in range(3):  # public APIs occasionally return empty/5xx; retry
        try:
            resp = requests.get(url, params=params, timeout=timeout, headers=hdrs)
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception:
            time.sleep(0.4 * (attempt + 1))
    if data is None:
        return None

    try:
        with open(path, "w") as fh:
            json.dump(data, fh)
        _record_index(key, url, params)
    except Exception:
        pass
    time.sleep(0.05)  # be polite
    return data
