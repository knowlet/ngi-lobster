from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_HEADERS = {
    "User-Agent": "ngi-lobster/0.1 (+https://github.com/knowlet/ngi-lobster)",
    "Accept": "application/json, application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
}


def fetch_text(url: str, *, params: dict | None = None, headers: dict | None = None, timeout: int = 20) -> str:
    if params:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{urlencode(params, doseq=True)}"
    req = Request(url, headers={**DEFAULT_HEADERS, **(headers or {})})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_json(url: str, *, params: dict | None = None, headers: dict | None = None, timeout: int = 20):
    return json.loads(fetch_text(url, params=params, headers=headers, timeout=timeout))
