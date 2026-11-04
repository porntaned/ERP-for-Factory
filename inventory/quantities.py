"""Quantity rule shared by every stock and manufacturing command (ledger precision).

A quantity is a finite Decimal, 0 < q < 10^14, representable at six fractional places.
Digits are inspected without rounding or depending on the caller's Decimal context;
trailing zeros beyond six places do not change representability.
"""

from decimal import Decimal

LIMIT = Decimal("100000000000000")


def is_positive_bounded(quantity: object) -> bool:
    return (
        isinstance(quantity, Decimal) and quantity.is_finite() and Decimal("0") < quantity < LIMIT
    )


def fits_six_places(quantity: Decimal) -> bool:
    _, digits, exponent = quantity.as_tuple()
    extra_places = -6 - exponent
    return not (extra_places > 0 and any(digits[-extra_places:]))


def is_valid_quantity(quantity: object) -> bool:
    return is_positive_bounded(quantity) and fits_six_places(quantity)
