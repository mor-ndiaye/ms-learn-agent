"""Client for the Microsoft Learn Catalog API.

The Microsoft Learn API is public and does not require authentication.
It returns the full catalog (~13 MB), so we cache it locally to avoid
re-downloading on every call.
"""

import json
import time
from pathlib import Path
from typing import Optional, Literal
from functools import cached_property

import httpx


class MsLearnClient:
    """Client for the Microsoft Learn Catalog API."""

    BASE_URL = "https://learn.microsoft.com/api/catalog/"
    CACHE_FILE = Path(".ms_learn_cache.json")
    CACHE_TTL_SECONDS = 60 * 60 * 24  # 24 hours

    def __init__(self, locale: str = "en-us"):
        self.locale = locale
        self._catalog: Optional[dict] = None

    def _is_cache_valid(self) -> bool:
        """Check if the local cache exists and is not too old."""
        if not self.CACHE_FILE.exists():
            return False
        age = time.time() - self.CACHE_FILE.stat().st_mtime
        return age < self.CACHE_TTL_SECONDS

    def _load_catalog(self) -> dict:
        """Load the catalog, using cache if available and fresh."""
        if self._is_cache_valid():
            with open(self.CACHE_FILE, "r") as f:
                return json.load(f)

        response = httpx.get(f"{self.BASE_URL}?locale={self.locale}", timeout=30.0)
        response.raise_for_status()  # ← raise an exception if 4xx/5xx
        catalog = response.json()  # parse the response
        with open(self.CACHE_FILE, "w") as f:
            json.dump(catalog, f)
        return catalog

    def _get_catalog(self) -> dict:
        """Return the catalog, loading it if not already in memory."""
        if self._catalog is None:
            self._catalog = self._load_catalog()
        return self._catalog

    def _score_module(self, module: dict, query_words: list[str]) -> float:
        title = (module.get("title") or "").lower()
        summary = (module.get("summary") or "").lower()
        title_hits = sum(1 for w in query_words if w in title)
        summary_hits = sum(1 for w in query_words if w in summary)

        return title_hits * 2 + summary_hits  # title weighted higher

    def search_modules(
        self,
        query: str,
        level: Literal["beginner", "intermediate", "advanced"] | None = None,
        max_results: int = 5,
    ) -> list[dict]:
        """Search for learning modules matching the query.

        Args:
            query: Keywords to match against title and summary.
            level: Optional filter — "beginner", "intermediate", or "advanced".
            max_results: Maximum number of modules to return.

        Returns:
            A list of simplified module dicts containing:
            - uid, title, summary, url, duration_in_minutes, levels, roles,     products
        """
        catalog: dict = self._get_catalog()
        modules: list[dict] = catalog.get("modules", [])
        query_words: list = query.lower().split()

        # 1. Score-and-filter ALL modules
        scored = []

        for module in modules:
            score = self._score_module(module, query_words)

            if score == 0:
                continue
            if level is not None and level not in (module.get("levels") or []):
                continue
            scored.append((score, module))

        # 2. Rank
        scored.sort(key=lambda pair: pair[0], reverse=True)

        # 3. Get top-K and simplify module object
        return [self._simplify(m) for _, m in scored[:max_results]]

    def _simplify(self, module: dict) -> dict:
        """Project a full module to the fields exposed to the agent."""
        return {
            "uid": module.get("uid"),
            "title": module.get("title"),
            "summary": module.get("summary"),
            "url": module.get("url"),
            "duration_in_minutes": module.get("duration_in_minutes"),
            "levels": module.get("levels"),
            "roles": module.get("roles"),
        }

    @cached_property
    def _modules_by_uid(self) -> dict[str, dict]:
        """
        Build dict containing all modules matched by key/value pair.
        e.g: "my-uid": {uid: "12ccjfd-675cfhs-66554", levels: [...], ...} # "key": {dict object}
        """
        return {m["uid"]: m for m in self._get_catalog()["modules"]}

    def get_module_details(self, uid: str) -> Optional[dict]:
        """Get full details for a specific module by its uid."""
        return self._modules_by_uid.get(uid)
