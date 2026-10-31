# stalecheck

**Catch numbers in your paper that no longer match your analysis.**

You re-run the analysis — a reviewer asked you to drop careless responders, you fixed a
bug, you added 12 participants — and the code now says `r = 0.688`. The paper still says
`r = 0.699` in Results, `.70` in the Abstract, and `118` degrees of freedom in a
parenthesis you forgot exists. stalecheck finds every one of them, tells you which run
changed it, and rewrites the ones it can safely rewrite.

```
STALE?  paper.md:5   untagged .70 -> .69 equals an OLD value of [r_sleep_score]
STALE   paper.md:13  0.699 -> 0.688  [r_sleep_score]  changed by analysis.py:20 @ 430c9b9
STALE   paper.md:14  118 -> 106  [df]                 changed by analysis.py:22 @ 430c9b9
STALE   paper.tex:5  42.5\% -> 46.3\%  [share_over_7h] changed by analysis.py:26 @ 430c9b9
```

## How it works

1. **Track** every number you report, in your analysis code:

   ```python
   from stalecheck import track
   r = track("r_sleep_score", statistics.correlation(sleep, score))
   ```

   Values go to `.stalecheck/results.json` with their **history**: each version keeps the
   git commit and `file:line` that produced it. Commit this file.

2. **Tag** the number where the manuscript prints it, written exactly as you want it shown:

   | Format   | Syntax                                   |
   |----------|------------------------------------------|
   | LaTeX    | `\sv{r_sleep_score}{0.699}` with `\newcommand{\sv}[2]{#2}` |
   | Markdown | `0.699<!--sv:r_sleep_score-->`           |

3. **Check**: `stalecheck check paper.tex` (exit code 1 if anything is stale, so it works as
   a pre-commit hook or in CI).

Numbers are compared **as written**, not as floats: `84.7\%` means "1 decimal, percent
scale", so it matches 0.8472 but not 0.8476. Rounding is half-up (what papers use, unlike
Python's `round`), and fixes keep the original style: `\%`, thousands separators, unicode
minus, and APA bare decimals (`.70 → .69`).

| Status    | Meaning |
|-----------|---------|
| `ok`      | Text matches the current value at its printed precision |
| `STALE`   | Text matches an *older* value; reports the run that changed it |
| `DIFF`    | Text matches no value the key ever had (typo / hand edit) |
| `?KEY`    | Tag refers to a key that was never tracked |
| `STALE?`  | (`--scan`) **untagged** number equal to an old value: probably stale |
| `tag?`    | (`--scan`) untagged number equal to a current value: consider tagging |

## Commands

```sh
stalecheck check paper.tex [--scan] [--json] [-v]
stalecheck fix paper.tex --write        # rewrite tagged stale numbers (dry run without --write)
stalecheck trace r_sleep_score paper.tex  # history + where it is cited
stalecheck list
stalecheck install-hook paper.tex       # block commits while the paper is stale
```

`fix` never touches untagged numbers: whether an untagged `0.85` in the abstract means
accuracy or something else is a judgement call. That is what the MCP server is for.

## MCP server (for coding agents)

`stalecheck-mcp` exposes the checks to an agent (Claude Code, Claude Desktop, Cursor…), so
after it edits your analysis it can ask "did that make the paper wrong?" — and handle the
judgement calls: deciding what an untagged number refers to (`tag_number`), and noticing
that "strongly associated" may no longer fit the new effect size.

| Tool | Does |
|------|------|
| `check_manuscript(path)` | stale / mismatched / untagged-stale numbers, with surrounding text |
| `fix_manuscript(path, dry_run=True)` | preview or apply rewrites of tagged numbers |
| `trace_value(key)` | full history: value, commit, source line, time |
| `list_values()` | all keys with current value |
| `tag_number(path, line, literal, key)` | attach a key to an untagged number |

Claude Code:

```sh
claude mcp add stalecheck -- /path/to/stalecheck/.venv/bin/stalecheck-mcp
```

## Install & test

```sh
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest            # 72 tests
PYTHON=.venv/bin/python example/demo.sh   # end-to-end demo in a temp git repo
```

## Limitations

- Untagged **integers** are not scanned (too many false positives: years, section numbers,
  citations). Tag sample sizes and degrees of freedom.
- Only numbers produced through `track()` are known. Numbers computed by hand in the text
  (e.g. a difference of two tracked values) need their own `track()` call.
- Word / Google Docs are not supported; export to Markdown, or keep numbers in LaTeX.
