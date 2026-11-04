"""
Simple in-memory + SQLite-backed cache for API responses.

Two-tier strategy:
  1. In-memory LRU (fast, per-process lifetime)
  2. SQLite (optional, survives restarts — enabled when PREFERENCE_STORAGE=local)

Usage:
    from travel_planner.utils.cache import cache
    result = await cache.get("weather:Paris:2024-04-01:2024-04-07")
    await cache.set("weather:Paris:2024-04-01:2024-04-07", data)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TTL = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
_USE_SQLITE = os.getenv("PREFERENCE_STORAGE", "session").lower() == "local"
_CACHE_DIR = Path(os.getenv("CACHE_DIR", ".cache"))
_DB_PATH = _CACHE_DIR / "travel_cache.db"
_MEM_MAX = 256  # max in-memory entries


def _make_key(*parts: str) -> str:
    raw = ":".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


class _MemoryCache:
    """Thread-safe LRU memory cache."""

    def __init__(self, maxsize: int = _MEM_MAX) -> None:
        self._store: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._maxsize = maxsize
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            self._store.move_to_end(key)
            return value

    async def set(self, key: str, value: Any, ttl: int = _TTL) -> None:
        async with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = (value, time.monotonic() + ttl)
            if len(self._store) > self._maxsize:
                self._store.popitem(last=False)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()


class _SqliteCache:
    """Persistent SQLite cache (used when PREFERENCE_STORAGE=local)."""

    def __init__(self) -> None:
        self._ready = False

    async def _ensure_ready(self) -> None:
        if self._ready:
            return
        try:
            import aiosqlite  # noqa: PLC0415

            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            async with aiosqlite.connect(_DB_PATH) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cache (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        expires_at REAL NOT NULL
                    )
                    """
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)"
                )
                await db.commit()
            self._ready = True
        except ImportError:
            logger.warning("aiosqlite not installed – SQLite cache disabled.")

    async def get(self, key: str) -> Any | None:
        await self._ensure_ready()
        if not self._ready:
            return None
        try:
            import aiosqlite  # noqa: PLC0415

            async with aiosqlite.connect(_DB_PATH) as db:
                async with db.execute(
                    "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
                ) as cursor:
                    row = await cursor.fetchone()
            if row is None:
                return None
            value_json, expires_at = row
            if time.time() > expires_at:
                await self.delete(key)
                return None
            return json.loads(value_json)
        except Exception as exc:  # pragma: no cover
            logger.warning("SQLite cache get error: %s", exc)
            return None

    async def set(self, key: str, value: Any, ttl: int = _TTL) -> None:
        await self._ensure_ready()
        if not self._ready:
            return
        try:
            import aiosqlite  # noqa: PLC0415

            async with aiosqlite.connect(_DB_PATH) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
                    (key, json.dumps(value), time.time() + ttl),
                )
                await db.commit()
        except Exception as exc:  # pragma: no cover
            logger.warning("SQLite cache set error: %s", exc)

    async def delete(self, key: str) -> None:
        if not self._ready:
            return
        try:
            import aiosqlite  # noqa: PLC0415

            async with aiosqlite.connect(_DB_PATH) as db:
                await db.execute("DELETE FROM cache WHERE key = ?", (key,))
                await db.commit()
        except Exception as exc:  # pragma: no cover
            logger.warning("SQLite cache delete error: %s", exc)

    async def clear(self) -> None:
        if not self._ready:
            return
        try:
            import aiosqlite  # noqa: PLC0415

            async with aiosqlite.connect(_DB_PATH) as db:
                await db.execute("DELETE FROM cache")
                await db.commit()
        except Exception as exc:  # pragma: no cover
            logger.warning("SQLite cache clear error: %s", exc)


class TwoTierCache:
    """
    Public cache façade: memory-first, falls through to SQLite when enabled.

    Example
    -------
    >>> result = await cache.get("weather:Paris:2024-04-01")
    >>> if result is None:
    ...     result = await fetch_weather(...)
    ...     await cache.set("weather:Paris:2024-04-01", result)
    """

    def __init__(self) -> None:
        self._mem = _MemoryCache()
        self._db = _SqliteCache() if _USE_SQLITE else None

    def make_key(self, *parts: str) -> str:
        """Create a deterministic cache key from arbitrary string parts."""
        return _make_key(*parts)

    async def get(self, key: str) -> Any | None:
        value = await self._mem.get(key)
        if value is not None:
            return value
        if self._db:
            value = await self._db.get(key)
            if value is not None:
                # Warm memory cache
                await self._mem.set(key, value)
        return value

    async def set(self, key: str, value: Any, ttl: int = _TTL) -> None:
        await self._mem.set(key, value, ttl)
        if self._db:
            await self._db.set(key, value, ttl)

    async def delete(self, key: str) -> None:
        await self._mem.delete(key)
        if self._db:
            await self._db.delete(key)

    async def clear(self) -> None:
        await self._mem.clear()
        if self._db:
            await self._db.clear()


# ── Module-level singleton ──────────────────────────────────────────────────
cache = TwoTierCache()
