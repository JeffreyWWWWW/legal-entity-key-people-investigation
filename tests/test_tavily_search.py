import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from tavily_search import TavilyError, main, search_tavily


def test_missing_api_key_returns_unavailable_for_fallback(capsys):
    exit_code = main(["Example Corp CTO"], environ={})

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output == {
        "provider": "tavily",
        "status": "unavailable",
        "reason": "missing_api_key",
        "results": [],
    }


def test_search_sends_expected_request_and_normalizes_results():
    captured = {}

    def transport(url, payload, timeout):
        captured.update(url=url, payload=payload, timeout=timeout)
        return {
            "answer": "Jane Doe leads research.",
            "results": [
                {
                    "title": "Leadership",
                    "url": "https://example.com/leadership",
                    "content": "Jane Doe is Chief Technology Officer.",
                    "score": 0.91,
                    "published_date": "2026-08-20",
                    "raw_content": "must not be persisted",
                }
            ],
        }

    output = search_tavily(
        "Example Corp CTO",
        api_key="test-key",
        max_results=3,
        search_depth="advanced",
        timeout=12,
        transport=transport,
    )

    assert captured == {
        "url": "https://api.tavily.com/search",
        "payload": {
            "api_key": "test-key",
            "query": "Example Corp CTO",
            "search_depth": "advanced",
            "max_results": 3,
            "include_answer": False,
            "include_raw_content": False,
        },
        "timeout": 12,
    }
    assert output == {
        "provider": "tavily",
        "status": "ok",
        "query": "Example Corp CTO",
        "results": [
            {
                "title": "Leadership",
                "url": "https://example.com/leadership",
                "snippet": "Jane Doe is Chief Technology Officer.",
                "score": 0.91,
                "published_date": "2026-08-20",
            }
        ],
    }


def test_api_failure_is_not_reported_as_no_results():
    def failing_transport(url, payload, timeout):
        raise TavilyError("HTTP 429: rate limited")

    with pytest.raises(TavilyError, match="429"):
        search_tavily(
            "Example Corp owner",
            api_key="test-key",
            transport=failing_transport,
        )


def test_rejects_blank_query_before_network_call():
    with pytest.raises(ValueError, match="query"):
        search_tavily("   ", api_key="test-key")
