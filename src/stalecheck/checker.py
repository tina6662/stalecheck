"""Compare a manuscript against the value registry, and rewrite stale numbers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import manuscript, numfmt

OK = "ok"
STALE = "stale"  # matches an older value of the key: we know which run changed it
MISMATCH = "mismatch"  # matches no value the key ever had (typo, wrong key, hand-edited)
UNKNOWN_KEY = "unknown_key"
UNTAGGED_CURRENT = "untagged_current"  # untagged, equals a current value: suggest tagging
UNTAGGED_STALE = "untagged_stale"  # untagged, equals only an old value: probably stale

PROBLEMS = {STALE, MISMATCH, UNKNOWN_KEY, UNTAGGED_STALE}


@dataclass
class Finding:
    kind: str
    file: str
    line: int
    literal: str
    keys: list[str] = field(default_factory=list)
    expected: str | None = None  # the literal rewritten with the current value
    current_value: float | None = None
    old_value: float | None = None
    changed_by: dict | None = None  # history entry that replaced the value the text shows
    start: int = 0
    end: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("start"), d.pop("end")
        return d


def _latest_match(lit: numfmt.Literal, history: list[dict]) -> tuple[int, int] | None:
    """Index and scale of the most recent history entry that renders as `lit`."""
    for i in range(len(history) - 1, -1, -1):
        scale = numfmt.match_scale(lit, history[i]["value"])
        if scale is not None:
            return i, scale
    return None


def check_tag(span: manuscript.Span, data: dict, file: str) -> Finding:
    f = Finding(kind=OK, file=file, line=span.line, literal=span.literal, keys=[span.key],
                start=span.start, end=span.end)
    history = data.get(span.key)
    if not history:
        f.kind = UNKNOWN_KEY
        return f
    current = history[-1]["value"]
    f.current_value = current
    lit = numfmt.parse_literal(span.literal)
    if lit is None:
        f.kind = MISMATCH
        return f
    hit = _latest_match(lit, history)
    if hit is None:
        f.kind = MISMATCH
        f.expected = numfmt.render(current, lit, numfmt.guess_scale(lit, current))
        return f
    i, scale = hit
    if i == len(history) - 1:
        return f
    # An older entry matches. If later entries round to the same text it is still fine.
    expected = numfmt.render(current, lit, scale)
    if expected == span.literal:
        return f
    f.kind = STALE
    f.expected = expected
    f.old_value = history[i]["value"]
    f.changed_by = history[i + 1]
    return f


def scan_candidate(span: manuscript.Span, data: dict, file: str) -> Finding | None:
    lit = numfmt.parse_literal(span.literal)
    if lit is None:
        return None
    current_keys, stale_keys = [], []
    for key, history in data.items():
        if numfmt.match_scale(lit, history[-1]["value"]) is not None:
            current_keys.append(key)
        elif _latest_match(lit, history[:-1]) is not None:
            stale_keys.append(key)
    if current_keys:
        return Finding(UNTAGGED_CURRENT, file, span.line, span.literal, sorted(current_keys),
                       start=span.start, end=span.end)
    if stale_keys:
        f = Finding(UNTAGGED_STALE, file, span.line, span.literal, sorted(stale_keys),
                    start=span.start, end=span.end)
        if len(stale_keys) == 1:
            history = data[stale_keys[0]]
            i, scale = _latest_match(lit, history[:-1])
            f.old_value, f.changed_by = history[i]["value"], history[i + 1]
            f.current_value = history[-1]["value"]
            f.expected = numfmt.render(f.current_value, lit, scale)
        return f
    return None


def check_text(text: str, data: dict, file: str = "<text>", *, latex: bool = False,
               scan: bool = False) -> list[Finding]:
    findings = [check_tag(s, data, file) for s in manuscript.find_tags(text, latex)]
    if scan:
        for s in manuscript.find_candidates(text, latex):
            f = scan_candidate(s, data, file)
            if f:
                findings.append(f)
    return sorted(findings, key=lambda f: f.start)


def check_file(path: str | Path, data: dict, *, scan: bool = False) -> list[Finding]:
    path = str(path)
    text = Path(path).read_text(encoding="utf-8")
    return check_text(text, data, path, latex=manuscript.is_latex(path), scan=scan)


def fix_text(text: str, data: dict, *, latex: bool = False) -> tuple[str, list[Finding]]:
    """Rewrite tagged stale/mismatched numbers to their current values.

    Untagged numbers are never rewritten: deciding what an untagged 0.85 means is a
    judgement call, left to the author (or to an agent via the MCP server).
    """
    fixable = [f for f in check_text(text, data, latex=latex)
               if f.kind in (STALE, MISMATCH) and f.expected is not None]
    for f in sorted(fixable, key=lambda f: f.start, reverse=True):
        text = text[:f.start] + f.expected + text[f.end:]
    return text, fixable


def fix_file(path: str | Path, data: dict, *, write: bool = False) -> list[Finding]:
    p = Path(path)
    new, fixed = fix_text(p.read_text(encoding="utf-8"), data, latex=manuscript.is_latex(str(p)))
    for f in fixed:
        f.file = str(path)
    if write and fixed:
        p.write_text(new, encoding="utf-8")
    return fixed


def usages(paths: list[str | Path], key: str) -> list[dict]:
    """Where a key is cited across manuscripts."""
    out = []
    for path in paths:
        text = Path(path).read_text(encoding="utf-8")
        for s in manuscript.find_tags(text, manuscript.is_latex(str(path))):
            if s.key == key:
                out.append({"file": str(path), "line": s.line, "literal": s.literal})
    return out
