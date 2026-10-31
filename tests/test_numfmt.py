from decimal import Decimal

import pytest

from stalecheck.numfmt import guess_scale, match_scale, parse_literal, quantize, render


@pytest.mark.parametrize("text, number, decimals, percent, thousands", [
    ("0.847", "0.847", 3, False, False),
    ("84.7%", "84.7", 1, True, False),
    ("84.7\\%", "84.7", 1, True, False),
    ("1,234.5", "1234.5", 1, False, True),
    ("-0.12", "-0.12", 2, False, False),
    ("−0.12", "-0.12", 2, False, False),
    (" 42 ", "42", 0, False, False),
    (".5", ".5", 1, False, False),
])
def test_parse_literal(text, number, decimals, percent, thousands):
    lit = parse_literal(text)
    assert lit.number == Decimal(number)
    assert (lit.decimals, lit.percent, lit.thousands) == (decimals, percent, thousands)


@pytest.mark.parametrize("text", ["", "abc", "1.2.3", "84.7 percent", "1,23"])
def test_parse_literal_rejects_non_numbers(text):
    assert parse_literal(text) is None


def test_half_up_rounding_avoids_float_artifacts():
    # Python's round(0.8465, 3) gives 0.846 (binary float); papers round half up.
    assert quantize(0.8465, 1, 3) == Decimal("0.847")
    assert quantize(0.125, 1, 2) == Decimal("0.13")


@pytest.mark.parametrize("literal, value, scale", [
    ("0.847", 0.8472, 1),
    ("84.7%", 0.8472, 100),
    ("84.7\\%", 0.8472, 100),
    ("84.7", 0.8472, 100),  # percent written without the sign
    ("84.7%", 84.72, 1),  # value already on percent scale
    ("1,234", 1234.4, 1),
    ("-0.31", -0.3149, 1),
])
def test_match_scale(literal, value, scale):
    assert match_scale(parse_literal(literal), value) == scale


@pytest.mark.parametrize("literal, value", [("0.847", 0.851), ("84.7%", 0.8476), ("0.31", -0.31)])
def test_match_scale_none(literal, value):
    assert match_scale(parse_literal(literal), value) is None


def test_percent_prefers_percent_scale():
    # 0.5 % of 1 vs 0.5: with a % sign the 100-scale reading wins
    assert match_scale(parse_literal("50%"), 0.5) == 100


@pytest.mark.parametrize("like, value, scale, out", [
    ("84.7\\%", 0.8513, 100, "85.1\\%"),
    ("84.7 %", 0.8513, 100, "85.1 %"),
    ("1,234.5", 12345.67, 1, "12,345.7"),
    ("−0.12", -0.256, 1, "−0.26"),
    ("-0.12", 0.256, 1, "0.26"),
    (" 0.85 ", 0.9, 1, " 0.90 "),
])
def test_render_keeps_style(like, value, scale, out):
    assert render(value, parse_literal(like), scale) == out


def test_guess_scale():
    assert guess_scale(parse_literal("84.7%"), 0.9) == 100
    assert guess_scale(parse_literal("0.847"), 0.9) == 1
    assert guess_scale(parse_literal("120"), 130.0) == 1
