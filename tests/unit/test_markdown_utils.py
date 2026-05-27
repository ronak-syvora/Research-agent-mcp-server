from datetime import datetime, timezone

from research_agent.utils.markdown import make_slug, timestamp_suffix


def test_slug_basic():
    assert make_slug("Integrating Chainlink into Solidity") == "integrating-chainlink-into-solidity"


def test_slug_strips_special_chars():
    s = make_slug("Add ⚡ Stripe (v2024) Webhooks!!!")
    assert " " not in s
    assert "(" not in s
    assert "!" not in s
    assert "stripe" in s


def test_slug_empty_fallback():
    assert make_slug("") == "report"
    assert make_slug("///") == "report"


def test_slug_respects_max_length():
    long = "a" * 200
    assert len(make_slug(long, max_length=30)) <= 30


def test_timestamp_format():
    t = datetime(2026, 5, 18, 9, 30, 45, tzinfo=timezone.utc)
    assert timestamp_suffix(t) == "20260518-093045"
