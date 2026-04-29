from app.services.retrieval_period import parse_ingestion_period_minutes


def test_parse_minutes_plain() -> None:
    assert parse_ingestion_period_minutes("5", default=3) == 5


def test_parse_minutes_suffix_m() -> None:
    assert parse_ingestion_period_minutes("10m", default=3) == 10


def test_parse_minutes_human_prefix() -> None:
    assert parse_ingestion_period_minutes("5 minutes", default=3) == 5


def test_parse_empty_uses_default() -> None:
    assert parse_ingestion_period_minutes(None, default=7) == 7
    assert parse_ingestion_period_minutes("", default=7) == 7
