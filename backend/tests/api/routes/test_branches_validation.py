import pytest
from fastapi import HTTPException

from app.api.routes.branches import _validate_gstin


def test_validate_gstin_accepts_valid_value() -> None:
    value = _validate_gstin("22AAAAA0000A1Z5")
    assert value == "22AAAAA0000A1Z5"


def test_validate_gstin_rejects_invalid_value() -> None:
    with pytest.raises(HTTPException):
        _validate_gstin("INVALID-GSTIN")
