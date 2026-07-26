"""Windows-compatible asyncio helpers for Playwright (and consumers using psycopg)."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Callable, Coroutine
from typing import cast


def configure_event_loop_policy() -> None:
    """Use SelectorEventLoop on Windows so psycopg async works in the main loop."""
    if sys.platform == "win32":
        # Still required for psycopg async on Windows under Python 3.12.
        asyncio.set_event_loop_policy(  # ty: ignore[deprecated]
            asyncio.WindowsSelectorEventLoopPolicy()
        )


def run[T](coro: Coroutine[object, object, T]) -> T:
    configure_event_loop_policy()
    return asyncio.run(coro)


def _run_in_fresh_loop[T](coro: Coroutine[object, object, T]) -> T:
    """Run a coroutine on a fresh loop (Proactor on Windows for Playwright)."""
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def run_playwright[T](factory: Callable[[], Coroutine[object, object, T]]) -> T:
    """Run Playwright/Crawl4AI work on a loop that supports subprocesses."""
    if sys.platform == "win32":
        return cast(T, await asyncio.to_thread(_run_in_fresh_loop, factory()))
    return await factory()
