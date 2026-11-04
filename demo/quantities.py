"""Display a quantity without trailing zeros and never in scientific notation.

Decimal.normalize() alone turns 30 into "3E+1"; the ":f" format keeps it "30".
"""

from decimal import Decimal


def format_quantity(value: Decimal) -> str:
    return f"{value.normalize():f}"
