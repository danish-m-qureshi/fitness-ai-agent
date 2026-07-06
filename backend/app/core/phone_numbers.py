import re


def normalize_phone_number(value: str | None) -> str | None:
    if value is None:
        return None

    digits = re.sub(r"\D", "", value.strip())
    if not digits:
        return None

    if digits.startswith("00"):
        digits = digits[2:]

    return f"+{digits}"
