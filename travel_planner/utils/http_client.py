"""
Shared async HTTP client with timeout, retry (max 2), and graceful fallback.

Usage:
    from travel_planner.utils.http_client import get, post

All functions raise HttpClientError on final failure so callers can catch it
and apply graceful degradation rather than crashing.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
_MAX_RETRIES = 2


class HttpClientError(Exception):
    """Raised when all retry attempts are exhausted or a non-retryable error occurs."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _is_retryable(exc: BaseException) -> bool:
    """Only retry on connection / timeout errors and 5xx responses."""
    if isinstance(exc, httpx.TimeoutException | httpx.ConnectError):
        return True
    if isinstance(exc, HttpClientError) and exc.status_code is not None:
        return exc.status_code >= 500
    return False


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(_MAX_RETRIES + 1),  # 1 initial + 2 retries
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    reraise=True,
)
async def _request(
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout = _DEFAULT_TIMEOUT,
) -> dict[str, Any] | list[Any]:
    """Low-level async request. Retried up to _MAX_RETRIES times."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method,
                url,
                params=params,
                json=json,
                headers=headers,
            )
        if response.status_code >= 400:
            raise HttpClientError(
                f"HTTP {response.status_code} for {url}: {response.text[:200]}",
                status_code=response.status_code,
            )
        return response.json()
    except httpx.TimeoutException as exc:
        logger.warning("Timeout on %s %s: %s", method, url, exc)
        raise
    except httpx.ConnectError as exc:
        logger.warning("Connect error on %s %s: %s", method, url, exc)
        raise
    except HttpClientError:
        raise
    except Exception as exc:
        logger.error("Unexpected error on %s %s: %s", method, url, exc)
        raise HttpClientError(str(exc)) from exc


async def get(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout = _DEFAULT_TIMEOUT,
) -> dict[str, Any] | list[Any]:
    """Async GET with retry and timeout.

    Args:
        url: Full URL to request.
        params: Query parameters.
        headers: Additional HTTP headers.
        timeout: httpx Timeout object.

    Returns:
        Parsed JSON response (dict or list).

    Raises:
        HttpClientError: After all retries are exhausted.
    """
    return await _request("GET", url, params=params, headers=headers, timeout=timeout)


async def post(
    url: str,
    *,
    json: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout = _DEFAULT_TIMEOUT,
) -> dict[str, Any] | list[Any]:
    """Async POST with retry and timeout.

    Args:
        url: Full URL to request.
        json: JSON body payload.
        headers: Additional HTTP headers.
        timeout: httpx Timeout object.

    Returns:
        Parsed JSON response (dict or list).

    Raises:
        HttpClientError: After all retries are exhausted.
    """
    return await _request("POST", url, json=json, headers=headers, timeout=timeout)
