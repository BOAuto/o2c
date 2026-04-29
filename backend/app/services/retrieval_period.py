"""Parse mailbox `ingestion_retrieval_period` string to minutes."""

import re


def parse_ingestion_period_minutes(value: str | None, default: int = 5) -> int:
    if value is None or not str(value).strip():
        return default
    s = str(value).strip().lower()
    try:
        if s.endswith("m") and not s.endswith("minutes"):
            return max(1, int(s[:-1].strip()))
        if s.endswith("s") and len(s) > 1 and s[-2].isdigit():
            return max(1, (int(s[:-1].strip()) + 59) // 60)
        if s.endswith("h") and not s.endswith("hours"):
            return max(1, int(s[:-1].strip()) * 60)
        parts = s.split()
        if parts and parts[0].isdigit():
            return max(1, int(parts[0]))
        m = re.match(r"^(\d+)", s)
        if m:
            return max(1, int(m.group(1)))
        return max(1, int(s))
    except ValueError:
        return default
