"""Explainable public BIN/IIN metadata classification.

This module classifies only provider-reported issuer metadata. It never infers
card validity, funds, 3-D Secure enrollment, authentication success, or payment
capability.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

NETWORKS = {"visa", "mastercard", "amex", "american express", "discover", "unionpay", "jcb", "diners"}
FUNDING_TYPES = {"credit", "debit", "prepaid"}
UNKNOWN = "unknown"


def _clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def classify_bin_metadata(data: dict[str, Any], *, source: str = "binlist.net",
                          retrieved_at: str | None = None) -> dict[str, str]:
    """Return normalized metadata and transparent confidence/quality labels."""
    if not isinstance(data, dict):
        data = {}

    country = data.get("country") if isinstance(data.get("country"), dict) else {}
    bank = data.get("bank") if isinstance(data.get("bank"), dict) else {}
    number = data.get("number") if isinstance(data.get("number"), dict) else {}

    scheme = _clean(data.get("scheme")).lower()
    card_type = _clean(data.get("type")).lower()
    brand = _clean(data.get("brand"))
    issuer = _clean(bank.get("name"))
    country_name = _clean(country.get("name"))
    country_code = _clean(country.get("alpha2")).upper()
    prepaid = data.get("prepaid")

    network = scheme if scheme in NETWORKS else (scheme or UNKNOWN)
    funding = card_type if card_type in FUNDING_TYPES else UNKNOWN
    product = brand or UNKNOWN

    populated = sum(bool(x) for x in (scheme, card_type, issuer, country_name, country_code))
    if populated >= 4:
        confidence = "provider_reported_rich"
    elif populated >= 2:
        confidence = "provider_reported_partial"
    else:
        confidence = "insufficient_metadata"

    issues: list[str] = []
    if scheme and scheme not in NETWORKS:
        issues.append("unrecognized_network_value")
    if card_type and card_type not in FUNDING_TYPES:
        issues.append("unrecognized_funding_value")
    if country_code and (len(country_code) != 2 or not country_code.isalpha()):
        issues.append("invalid_country_code")
    if isinstance(prepaid, bool) and card_type == "credit" and prepaid:
        issues.append("prepaid_credit_metadata_conflict")
    if not scheme and not card_type and not issuer and not country_name:
        posture = "no_classifiable_metadata"
    elif issues:
        posture = "metadata_inconsistent"
    elif confidence == "insufficient_metadata":
        posture = "metadata_incomplete"
    else:
        posture = "metadata_consistent"

    stamp = retrieved_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "network": network,
        "funding_type": funding,
        "product_category": product,
        "issuer": issuer or UNKNOWN,
        "issuer_country": country_code or country_name or UNKNOWN,
        "prepaid": str(prepaid).lower() if isinstance(prepaid, bool) else UNKNOWN,
        "metadata_confidence": confidence,
        "security_posture": posture,
        "quality_flags": ",".join(issues) if issues else "none",
        "metadata_source": source,
        "retrieved_at": stamp,
        "authentication_status": "not_tested",
        "real_card_3ds_status": "unknown",
    }
