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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _extract_value(
    node,
    selector: str | None = None,
    attribute: str | None = None,
):
    """
    Extract a value from a record.

    If selector is provided, locate the matching element first.
    If attribute is provided, return that attribute from the
    matched element. Otherwise, return the matched element's text.

    If no selector is provided, operate directly on the record node.
    """

    if selector:
        # select_one() searches descendants, so explicitly handle
        # the case where the record node itself matches the selector.
        try:
            if node.name and node in node.select(selector):
                child = node
            else:
                child = node.select_one(selector)
        except Exception:
            child = node.select_one(selector)

        if child is None:
            return None
    else:
        child = node

    if attribute:
        value = child.get(attribute)
    else:
        value = child.get_text(" ", strip=True)

    if isinstance(value, str):
        value = value.strip()

    return value


def validate(
    target: dict[str, Any],
    html: str | None,
) -> ValidationResult:
    """
    Validate the returned HTML against the target extraction
    specification.
    """

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

    # Exact record count.
    if expected_records is not None and records_found != expected_records:
        return ValidationResult(
            passed=False,
            reason="unexpected_record_count",
            records_found=records_found,
            records_expected=expected_records,
        )

    # Minimum record count.
    if min_records is not None and records_found < min_records:
        return ValidationResult(
            passed=False,
            reason="insufficient_records",
            records_found=records_found,
            records_expected=min_records,
        )

    if records_found == 0:
        return ValidationResult(
            passed=False,
            reason="no_records_found",
            records_found=0,
            records_expected=expected_records or min_records,
        )

    extracted_records: list[dict[str, Any]] = []

    for record_index, record in enumerate(records, start=1):
        extracted: dict[str, Any] = {}

        for field_name, spec in fields_spec.items():

            # Support the simple form:
            #
            # product_name: 'h2.product-name'
            #
            if isinstance(spec, str):
                selector = spec
                attribute = None
                expected_text = None
                fallback = None

            else:
                selector = spec.get("selector")
                attribute = spec.get("attribute")
                expected_text = spec.get("expected_text")
                fallback = spec.get("fallback")

            value = _extract_value(
                record,
                selector=selector,
                attribute=attribute,
            )

            # Optional fallback.
            if value is None and fallback:
                fallback_selector = fallback.get("selector")
                fallback_attribute = fallback.get("attribute")

                value = _extract_value(
                    record,
                    selector=fallback_selector,
                    attribute=fallback_attribute,
                )

            extracted[field_name] = value

            # Required field must contain a value.
            if value is None or (isinstance(value, str) and not value):
                return ValidationResult(
                    passed=False,
                    reason=(
                        f"missing_required_field:"
                        f"{field_name}:"
                        f"record_{record_index}"
                    ),
                    records_found=records_found,
                    records_expected=(expected_records or min_records),
                    fields=extracted_records,
                )

            # Exact expected text, when configured.
            if expected_text is not None and value != expected_text:
                return ValidationResult(
                    passed=False,
                    reason=(
                        f"unexpected_field_text:"
                        f"{field_name}:"
                        f"record_{record_index}"
                    ),
                    records_found=records_found,
                    records_expected=(expected_records or min_records),
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
