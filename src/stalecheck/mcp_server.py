"""MCP server: lets a coding agent ask "did my change make the paper wrong?"

The deterministic checks live in `checker`; the agent supplies the judgement the
tool deliberately refuses to make (what an untagged number refers to, whether a
sentence like "significantly better" still holds after the numbers moved).
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.mcpserver import MCPServer

from . import checker, manuscript, store

server = MCPServer(
    name="stalecheck",
    instructions=(
        "Use after changing analysis code or data. check_manuscript reports numbers in the "
        "paper that no longer match tracked results. Fix tagged ones with fix_manuscript; for "
        "untagged ones, read the surrounding sentence before editing, and also check whether "
        "wording such as 'outperforms' or 'significant' is still true for the new numbers."
    ),
)


def _data(path: str, store_path: str | None) -> dict:
    return store.load(Path(store_path) if store_path else store.find_store(Path(path).parent))


def _context(path: str, line: int, radius: int = 1) -> str:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[max(0, line - 1 - radius): line + radius])


@server.tool()
def check_manuscript(path: str, scan_untagged: bool = True, store_path: str | None = None) -> dict:
    """Report numbers in a .tex/.md manuscript that are stale relative to tracked analysis results.

    Each problem includes the file line, the literal as written, the suggested replacement,
    and the history entry (source file:line, git commit, time) that changed the value.
    """
    findings = checker.check_file(path, _data(path, store_path), scan=scan_untagged)
    problems = []
    for f in findings:
        if f.kind == checker.OK:
            continue
        d = f.to_dict()
        d["context"] = _context(path, f.line)
        problems.append(d)
    return {
        "up_to_date": sum(f.kind == checker.OK for f in findings),
        "problems": problems,
        "needs_attention": any(f.kind in checker.PROBLEMS for f in findings),
    }


@server.tool()
def fix_manuscript(path: str, dry_run: bool = True, store_path: str | None = None) -> dict:
    """Rewrite tagged stale numbers to their current values, keeping each number's formatting.

    Untagged numbers are never changed. Call with dry_run=True first to preview.
    """
    fixed = checker.fix_file(path, _data(path, store_path), write=not dry_run)
    return {
        "dry_run": dry_run,
        "changes": [{"line": f.line, "old": f.literal, "new": f.expected, "key": f.keys[0]} for f in fixed],
    }


@server.tool()
def trace_value(key: str, manuscripts: list[str] | None = None, store_path: str | None = None) -> dict:
    """Full history of one tracked value (every version, with the commit and code location that
    produced it), plus where manuscripts cite it."""
    data = store.load(Path(store_path) if store_path else store.find_store())
    return {"key": key, "history": data.get(key, []), "cited_at": checker.usages(manuscripts or [], key)}


@server.tool()
def list_values(store_path: str | None = None) -> dict:
    """All tracked keys with their current value and number of versions."""
    data = store.load(Path(store_path) if store_path else store.find_store())
    return {k: {"current": h[-1]["value"], "versions": len(h)} for k, h in sorted(data.items())}


@server.tool()
def tag_number(path: str, line: int, literal: str, key: str) -> dict:
    """Attach a key to an untagged number on a given line (first occurrence), so future checks
    and fixes cover it. Use after confirming from context which result the number reports."""
    p = Path(path)
    lines = p.read_text(encoding="utf-8").split("\n")
    if not 1 <= line <= len(lines) or literal not in lines[line - 1]:
        return {"ok": False, "error": f"{literal!r} not found on line {line}"}
    tagged = f"\\sv{{{key}}}{{{literal}}}" if manuscript.is_latex(path) else f"{literal}<!--sv:{key}-->"
    lines[line - 1] = lines[line - 1].replace(literal, tagged, 1)
    p.write_text("\n".join(lines), encoding="utf-8")
    return {"ok": True, "line": line, "now": lines[line - 1].strip()}


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()
