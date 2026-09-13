from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from bs4 import BeautifulSoup


@dataclass
class ValidationResult:
    passed: bool
    reason: str | None
    records_found: int | None = None
    records_expected: int | None = None
    fields: list[dict[str, Any]] | None = None

    def to_dict(self):
        return asdict(self)


def _extract_value(node, selector, attribute=None):
    child = node.select_one(selector)

    if child is None:
        return None

    if attribute:
        value = child.get(attribute)
    else:
        value = child.get_text(" ", strip=True)

    if isinstance(value, str):
        value = value.strip()

    return value


def validate(target, html):
    if not html:
        return ValidationResult(
            passed=False,
            reason="empty_response",
        )

    extraction = target.get("extraction") or {}
    record_selector = extraction.get("record_selector")
    fields_spec = extraction.get("fields") or {}

    expected_records = extraction.get("expected_records")
    min_records = extraction.get("min_records")

    if not record_selector or not fields_spec:
        return ValidationResult(
            passed=False,
            reason="extraction_spec_not_configured",
        )

    soup = BeautifulSoup(html, "html.parser")

    records = soup.select(record_selector)
    records_found = len(records)

    # Exact record count requirement
    if expected_records is not None and records_found != expected_records:
        return ValidationResult(
            passed=False,
            reason="unexpected_record_count",
            records_found=records_found,
            records_expected=expected_records,
        )

    # Minimum record count requirement
    if min_records is not None and records_found < min_records:
        return ValidationResult(
            passed=False,
            reason="insufficient_records",
            records_found=records_found,
            records_expected=min_records,
        )

    # No records at all
    if records_found == 0:
        return ValidationResult(
            passed=False,
            reason="no_records_found",
            records_found=0,
            records_expected=expected_records or min_records,
        )

    extracted_records = []

    for record_index, record in enumerate(records, start=1):
        extracted = {}

        for field_name, spec in fields_spec.items():

            if isinstance(spec, str):
                selector = spec
                attribute = None
                expected_text = None
            else:
                selector = spec["selector"]
                attribute = spec.get("attribute")
                expected_text = spec.get("expected_text")

            value = _extract_value(
                record,
                selector,
                attribute,
            )

            extracted[field_name] = value

            # Required field must exist and contain a value.
            if value is None or (isinstance(value, str) and not value):
                return ValidationResult(
                    passed=False,
                    reason=(
                        f"missing_required_field:" f"{field_name}:record_{record_index}"
                    ),
                    records_found=records_found,
                    records_expected=expected_records or min_records,
                    fields=extracted_records,
                )

            # Field must match expected text when configured.
            if expected_text is not None and value != expected_text:
                return ValidationResult(
                    passed=False,
                    reason=(
                        f"unexpected_field_text:" f"{field_name}:record_{record_index}"
                    ),
                    records_found=records_found,
                    records_expected=expected_records or min_records,
                    fields=extracted_records,
                )

        extracted_records.append(extracted)

    return ValidationResult(
        passed=True,
        reason=None,
        records_found=records_found,
        records_expected=expected_records or min_records,
        fields=extracted_records,
    )
