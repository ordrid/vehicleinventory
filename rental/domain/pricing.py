"""What a rental costs.

The base amount, the optional extras and any late charge. Pure arithmetic: no
app context, no database, and no clock -- every time is passed in, so a test can
price a rental in 2019 or 2031 without mocking anything.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

PESO = Decimal("0.01")


def money(value) -> Decimal:
    """Quantise to two decimal places, rounding half up.

    Every amount this module returns has passed through here, so a total can
    never carry the long tail of a division.
    """
    return Decimal(value).quantize(PESO, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Duration:
    """How long a rental runs, in the several shapes the pricing needs.

    `hours` and `billable_days` are separate on purpose. The base rental may bill
    the remainder of a day by the hour, while a per-day extra like insurance
    charges a whole day for that same remainder. Conflating them is how a
    25-hour rental ends up charging one day of insurance.
    """

    hours: int
    full_days: int
    extra_hours: int
    billable_days: int


def duration_between(pickup_at: datetime, return_at: datetime) -> Duration:
    """Measure a rental, rounding part hours up.

    Both datetimes must be naive -- the system stores and compares naive local
    times (see rental/clock.py). A non-positive span raises, because that is a
    validation failure the caller should already have refused, not a rental
    that costs nothing.
    """
    if return_at <= pickup_at:
        raise ValueError("A rental must end after it begins.")

    hours = max(1, math.ceil((return_at - pickup_at).total_seconds() / 3600))
    return Duration(
        hours=hours,
        full_days=hours // 24,
        extra_hours=hours % 24,
        billable_days=max(1, math.ceil(hours / 24)),
    )
