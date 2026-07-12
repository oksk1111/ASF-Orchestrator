"""수집기 공통 정의."""

from __future__ import annotations


class CollectorError(Exception):
    """수집 실패(인증 오류, HTTP 오류, 파싱 오류 등)를 나타낸다."""


def to_int(value: object, default: int = 0) -> int:
    """숫자 문자열/실수를 int로 안전 변환한다. 실패 시 default."""
    if value is None:
        return default
    try:
        s = str(value).replace(",", "").strip()
        if s in ("", "-", "."):
            return default
        return int(float(s))
    except (ValueError, TypeError):
        return default
