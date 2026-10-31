"""stalecheck command line: check, fix, trace, list, install-hook."""

from __future__ import annotations

import argparse
import json
import shlex
import stat
import sys
from pathlib import Path

from . import checker, store

ICONS = {
    checker.OK: "ok   ",
    checker.STALE: "STALE",
    checker.MISMATCH: "DIFF ",
    checker.UNKNOWN_KEY: "?KEY ",
    checker.UNTAGGED_CURRENT: "tag? ",
    checker.UNTAGGED_STALE: "STALE?",
}


def describe(f: checker.Finding) -> str:
    where = f"{f.file}:{f.line}"
    keys = ", ".join(f.keys)
    if f.kind == checker.OK:
        return f"{where}  {f.literal}  [{keys}]"
    if f.kind == checker.STALE:
        by = f.changed_by or {}
        return (f"{where}  {f.literal} -> {f.expected}  [{keys}]  "
                f"changed by {by.get('source')} @ {by.get('commit')} ({by.get('time')})")
    if f.kind == checker.MISMATCH:
        hint = f" (current value renders as {f.expected})" if f.expected else ""
        return f"{where}  {f.literal} matches no value [{keys}] ever had{hint}"
    if f.kind == checker.UNKNOWN_KEY:
        return f"{where}  unknown key [{keys}]: was it ever track()ed?"
    if f.kind == checker.UNTAGGED_CURRENT:
        return f"{where}  untagged {f.literal} equals current [{keys}]: consider tagging it"
    hint = f" -> {f.expected}" if f.expected else ""
    return f"{where}  untagged {f.literal}{hint} equals an OLD value of [{keys}]"


def _store(args) -> Path:
    if args.store:
        return Path(args.store)
    return store.find_store(Path(args.files[0]).parent if getattr(args, "files", None) else None)


def cmd_check(args) -> int:
    data = store.load(_store(args))
    findings = [f for p in args.files for f in checker.check_file(p, data, scan=args.scan)]
    problems = [f for f in findings if f.kind in checker.PROBLEMS]
    if args.json:
        print(json.dumps([f.to_dict() for f in findings], indent=2, ensure_ascii=False))
    else:
        for f in findings:
            if f.kind != checker.OK or args.verbose:
                print(f"{ICONS[f.kind]}  {describe(f)}")
        n_ok = sum(f.kind == checker.OK for f in findings)
        print(f"\n{n_ok} up to date, {len(problems)} problem(s)", file=sys.stderr)
    return 1 if problems else 0


def cmd_fix(args) -> int:
    data = store.load(_store(args))
    total = 0
    for p in args.files:
        for f in checker.fix_file(p, data, write=args.write):
            total += 1
            print(f"{f.file}:{f.line}  {f.literal} -> {f.expected}  [{', '.join(f.keys)}]")
    verb = "rewrote" if args.write else "would rewrite (pass --write)"
    print(f"\n{verb} {total} number(s)", file=sys.stderr)
    return 0


def cmd_trace(args) -> int:
    data = store.load(_store(args))
    history = data.get(args.key)
    if not history:
        print(f"no history for {args.key!r}", file=sys.stderr)
        return 1
    for i, e in enumerate(history):
        mark = "*" if i == len(history) - 1 else " "
        print(f"{mark} {e['value']!r:<22} {e.get('commit') or '-':<16} {e.get('source') or '-':<28} {e['time']}")
    for u in checker.usages(args.files, args.key):
        print(f"  cited at {u['file']}:{u['line']} as {u['literal']}")
    return 0


def cmd_list(args) -> int:
    data = store.load(_store(args))
    for key in sorted(data):
        h = data[key]
        print(f"{key:<28} {h[-1]['value']!r:<22} ({len(h)} version{'s' * (len(h) != 1)})")
    return 0


def cmd_install_hook(args) -> int:
    hook = Path(".git/hooks/pre-commit")
    if not hook.parent.is_dir():
        print("not at the root of a git repository", file=sys.stderr)
        return 1
    line = f"{shlex.quote(sys.executable)} -m stalecheck check {' '.join(map(shlex.quote, args.files))}"
    if hook.exists() and "stalecheck" not in hook.read_text():
        print(f"{hook} exists and is not ours; add this line to it yourself:\n{line}", file=sys.stderr)
        return 1
    hook.write_text(f"#!/bin/sh\n# installed by stalecheck\n{line}\n")
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"installed {hook}: {line}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stalecheck", description=__doc__)
    p.add_argument("--store", help="path to results.json (default: nearest .stalecheck/)")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="report stale numbers; exit 1 if any")
    c.add_argument("files", nargs="+")
    c.add_argument("--scan", action="store_true", help="also look at untagged numbers")
    c.add_argument("--json", action="store_true")
    c.add_argument("-v", "--verbose", action="store_true", help="also list up-to-date numbers")
    c.set_defaults(func=cmd_check)

    f = sub.add_parser("fix", help="rewrite tagged stale numbers to current values")
    f.add_argument("files", nargs="+")
    f.add_argument("--write", action="store_true", help="modify files (default: dry run)")
    f.set_defaults(func=cmd_fix)

    t = sub.add_parser("trace", help="show a key's history and where it is cited")
    t.add_argument("key")
    t.add_argument("files", nargs="*")
    t.set_defaults(func=cmd_trace)

    ls = sub.add_parser("list", help="list tracked keys")
    ls.set_defaults(func=cmd_list)

    h = sub.add_parser("install-hook", help="run `check` as a git pre-commit hook")
    h.add_argument("files", nargs="+")
    h.set_defaults(func=cmd_install_hook)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
