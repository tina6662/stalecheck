"""Find tagged numbers (and untagged candidates) in LaTeX / Markdown manuscripts.

LaTeX:     \\sv{main_acc}{84.7\\%}       with  \\newcommand{\\sv}[2]{#2}
Markdown:  84.7%<!--sv:main_acc-->
"""

from __future__ import annotations

import re
from dataclasses import dataclass

LATEX_TAG = re.compile(r"\\sv\{(?P<key>[A-Za-z0-9_.:-]+)\}\{(?P<lit>[^{}]*)\}")
MD_TAG = re.compile(
    r"(?P<lit>[-+\u2212]?(?:\d{1,3}(?:,\d{3})+|\d+)?\.?\d+(?:\s*\\?%)?)\s*<!--\s*sv:(?P<key>[A-Za-z0-9_.:-]+)\s*-->"
)
# Untagged candidates: must have a decimal point or a percent sign, so we skip
# section numbers, years, and citations like [12].
CANDIDATE = re.compile(
    r"(?<![\w.\\])[-\u2212]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)?\.\d+(?:\s*\\?%)?|\d+\s*\\?%)(?![\w.]*\d)"
)
LATEX_COMMENT = re.compile(r"(?<!\\)%.*")


@dataclass(frozen=True)
class Span:
    key: str | None  # None for untagged candidates
    literal: str
    start: int  # offsets of the literal itself, so fixes replace only the number
    end: int
    line: int


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _blank(text: str, start: int, end: int) -> str:
    return text[:start] + re.sub(r"[^\n]", " ", text[start:end]) + text[end:]


def mask_latex_comments(text: str) -> str:
    """Blank out % comments (keeping offsets) so commented-out numbers are ignored."""
    for m in reversed(list(LATEX_COMMENT.finditer(text))):
        text = _blank(text, m.start(), m.end())
    return text


def is_latex(path: str) -> bool:
    return path.endswith((".tex", ".ltx"))


def find_tags(text: str, latex: bool) -> list[Span]:
    scan = mask_latex_comments(text) if latex else text
    spans = []
    for m in LATEX_TAG.finditer(scan):
        spans.append(Span(m["key"], m["lit"], m.start("lit"), m.end("lit"), line_of(text, m.start())))
    for m in MD_TAG.finditer(scan):
        spans.append(Span(m["key"], m["lit"], m.start("lit"), m.end("lit"), line_of(text, m.start())))
    return sorted(spans, key=lambda s: s.start)


def find_candidates(text: str, latex: bool) -> list[Span]:
    """Numbers that look like reported results but carry no tag."""
    scan = mask_latex_comments(text) if latex else text
    for m in list(LATEX_TAG.finditer(scan)) + list(MD_TAG.finditer(scan)):
        scan = _blank(scan, m.start(), m.end())
    return [
        Span(None, m.group(), m.start(), m.end(), line_of(text, m.start()))
        for m in CANDIDATE.finditer(scan)
    ]
