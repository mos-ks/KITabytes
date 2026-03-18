from __future__ import annotations

import pytest

from app.services.data_service import _build_filter, _extract_summary_params


def test_build_filter_uses_case_insensitive_regex() -> None:
    query = _build_filter(customer="Acme", material="steel", test_type="tensile", test_program="prog-1")

    assert query == {
        "TestParametersFlat.CUSTOMER": {"$regex": "Acme", "$options": "i"},
        "TestParametersFlat.MATERIAL": {"$regex": "steel", "$options": "i"},
        "TestParametersFlat.TYPE_OF_TESTING_STR": {"$regex": "tensile", "$options": "i"},
        "testProgramId": {"$regex": "prog-1", "$options": "i"},
    }


def test_extract_summary_params_keeps_key_fields_only() -> None:
    summary = _extract_summary_params(
        {
            "TestParametersFlat": {
                "CUSTOMER": "Acme",
                "MATERIAL": "Aluminum",
                "STANDARD": "ISO 6892",
                "IGNORED": "value",
            }
        }
    )

    assert summary == {
        "CUSTOMER": "Acme",
        "MATERIAL": "Aluminum",
        "STANDARD": "ISO 6892",
    }
