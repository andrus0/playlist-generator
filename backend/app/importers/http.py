"""Polite HTTP client shared by the scrapers: identifies itself, throttles, retries."""

import logging
import time

import httpx

log = logging.getLogger(__name__)

USER_AGENT = "PlaylistGeneratorBot/0.1 (+https://github.com/andrus0/playlist-generator)"


class PoliteClient:
    def __init__(self, min_interval: float = 1.0, timeout: float = 30.0, max_backoff: float = 60):
        self.min_interval = min_interval
        self.max_backoff = max_backoff
        self._last = 0.0
        self._client = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept-Language": "de,en;q=0.8"},
            timeout=timeout,
            follow_redirects=True,
        )

    def get(self, url: str, params: dict | None = None, retries: int = 6) -> httpx.Response:
        for attempt in range(retries + 1):
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            try:
                r = self._client.get(url, params=params)
            except httpx.HTTPError as exc:
                if attempt == retries:
                    raise
                delay = min(2.0**attempt * 2, self.max_backoff)  # 2,4,8,16,32,60 s
                log.warning("%s: %s – retrying in %.0fs", url, exc, delay)
                time.sleep(delay)
                continue
            if r.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                retry_after = r.headers.get("Retry-After", "")
                delay = float(retry_after) if retry_after.isdigit() else 2.0**attempt + 1
                delay = min(delay, self.max_backoff)
                log.warning("%s: HTTP %s – retrying in %.0fs", url, r.status_code, delay)
                time.sleep(delay)
                continue
            if r.status_code in (401, 403):
                raise PermissionError(f"{url}: HTTP {r.status_code} – blocked, aborting")
            return r
        raise RuntimeError("unreachable")

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
