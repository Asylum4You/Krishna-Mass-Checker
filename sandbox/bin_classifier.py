"""Public BIN/IIN metadata classification; deliberately excludes card/auth status."""

def classify_bin_metadata(data: dict) -> dict[str, str]:
    country = data.get("country") or {}
    bank = data.get("bank") or {}
    return {
        "Scheme": str(data.get("scheme") or ""),
        "Brand": str(data.get("brand") or ""),
        "Card type": str(data.get("type") or ""),
        "Country": str(country.get("name") or ""),
        "Bank / issuer": str(bank.get("name") or ""),
        "3-D Secure / VBV status": "Not tested",
    }
