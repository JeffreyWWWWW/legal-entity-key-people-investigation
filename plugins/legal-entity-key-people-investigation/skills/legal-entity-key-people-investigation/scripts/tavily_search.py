#!/usr/bin/env python3
"""Search Tavily for investigation leads and emit normalized JSON."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Callable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class TavilyError(RuntimeError):
    """Raised when Tavily cannot return a trustworthy search response."""


Transport = Callable[[str, dict[str, Any], float], Mapping[str, Any]]


def _http_transport(
    url: str, payload: dict[str, Any], timeout: float
) -> Mapping[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        message = f"HTTP {exc.code}"
        if detail:
            message = f"{message}: {detail}"
        raise TavilyError(message) from exc
    except URLError as exc:
        raise TavilyError(f"network error: {exc.reason}") from exc

    try:
        result = json.loads(body)
    except json.JSONDecodeError as exc:
        raise TavilyError("Tavily returned invalid JSON") from exc
    if not isinstance(result, dict):
        raise TavilyError("Tavily returned an unexpected response")
    return result


def search_tavily(
    query: str,
    *,
    api_key: str,
    max_results: int = 5,
    search_depth: str = "advanced",
    timeout: float = 20,
    transport: Transport = _http_transport,
) -> dict[str, Any]:
    query = query.strip()
    if not query:
        raise ValueError("query must not be blank")
    if not api_key:
        raise ValueError("api_key must not be blank")
    if not 1 <= max_results <= 20:
        raise ValueError("max_results must be between 1 and 20")
    if search_depth not in {"basic", "advanced"}:
        raise ValueError("search_depth must be basic or advanced")

    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": search_depth,
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False,
    }
    response = transport(TAVILY_SEARCH_URL, payload, timeout)
    raw_results = response.get("results", [])
    if not isinstance(raw_results, list):
        raise TavilyError("Tavily response field 'results' is not a list")

    results = []
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not isinstance(url, str) or not url.strip():
            continue
        results.append(
            {
                "title": item.get("title", ""),
                "url": url,
                "snippet": item.get("content", ""),
                "score": item.get("score"),
                "published_date": item.get("published_date"),
            }
        )

    return {
        "provider": "tavily",
        "status": "ok",
        "query": query,
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search Tavily for legal-entity investigation leads."
    )
    parser.add_argument("query", help="Search query")
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument(
        "--search-depth", choices=("basic", "advanced"), default="advanced"
    )
    parser.add_argument("--timeout", type=float, default=20)
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    environment = os.environ if environ is None else environ
    api_key = environment.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        print(
            json.dumps(
                {
                    "provider": "tavily",
                    "status": "unavailable",
                    "reason": "missing_api_key",
                    "results": [],
                },
                ensure_ascii=False,
            )
        )
        return 0

    try:
        output = search_tavily(
            args.query,
            api_key=api_key,
            max_results=args.max_results,
            search_depth=args.search_depth,
            timeout=args.timeout,
        )
    except (TavilyError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "provider": "tavily",
                    "status": "error",
                    "reason": str(exc),
                    "results": [],
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1

    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
