"""How a number is written in a manuscript, and whether it still matches a value.

A literal like "84.7\\%" carries its own formatting contract: 1 decimal place,
percent scale, LaTeX-escaped percent sign. We compare values *as they would be
written* (half-up rounding at the literal's precision), never as raw floats.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

LITERAL_RE = re.compile(
    r"^(?P<lead>\s*)(?P<sign>[-+−]?)"
    r"(?P<num>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)"
    r"(?P<pct>\s*\\?%)?(?P<trail>\s*)$"
)

SCALES = (1, 100)


@dataclass(frozen=True)
class Literal:
    text: str
    number: Decimal
    decimals: int
    percent: bool
    thousands: bool
    sign_char: str  # "-" or unicode minus, kept when re-rendering
    pct_text: str  # e.g. "%", "\\%", " %"
    lead: str
    trail: str


def parse_literal(text: str) -> Literal | None:
    m = LITERAL_RE.match(text)
    if not m:
        return None
    raw = m["num"]
    digits = raw.replace(",", "")
    try:
        number = Decimal(digits)
    except InvalidOperation:
        return None
    sign = m["sign"]
    if sign in ("-", "−"):
        number = -number
    decimals = len(raw.split(".", 1)[1]) if "." in raw else 0
    return Literal(
        text=text,
        number=number,
        decimals=decimals,
        percent=bool(m["pct"]),
        thousands="," in raw,
        sign_char="−" if sign == "−" else "-",
        pct_text=m["pct"] or "",
        lead=m["lead"],
        trail=m["trail"],
    )


def quantize(value: float, scale: int, decimals: int) -> Decimal:
    # str() first so 0.8465 stays 0.8465 instead of 0.84649999...
    d = Decimal(str(value)) * scale
    return d.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)


def match_scale(lit: Literal, value: float) -> int | None:
    """Return the scale (1 or 100) under which `value` renders as `lit`, else None."""
    order = (100, 1) if lit.percent else SCALES
    for scale in order:
        if quantize(value, scale, lit.decimals) == lit.number:
            return scale
    return None


def guess_scale(lit: Literal, value: float) -> int:
    """Best guess at the intended scale when nothing matches (for suggested fixes)."""
    if abs(value) <= 1 and (lit.percent or abs(lit.number) > 1):
        return 100
    return 1


def render(value: float, like: Literal, scale: int) -> str:
    """Write `value` in the same style as `like`."""
    q = quantize(value, scale, like.decimals)
    body = f"{abs(q):,.{like.decimals}f}" if like.thousands else f"{abs(q):.{like.decimals}f}"
    sign = like.sign_char if q < 0 else ""
    return f"{like.lead}{sign}{body}{like.pct_text}{like.trail}"
