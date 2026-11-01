# stalecheck

[English](#stalecheck) | [繁體中文](#繁體中文說明)

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
claude mcp add -s user stalecheck -- /path/to/stalecheck/.venv/bin/stalecheck-mcp
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

---

## 繁體中文說明

**自動抓出論文中已經跟分析結果不一致的數字。**

分析常常要重跑：reviewer 要求排除沒認真作答的受試者、修了一個 bug、多收了 12 位受試者。程式現在算出 `r = 0.688`，論文的 Results 卻還寫 `r = 0.699`，Abstract 寫 `.70`，某個括號裡的自由度也還是 `118`。stalecheck 會找出這些數字，指出是哪一次執行改變了它們，並自動改寫可以安全改寫的部分。

### 運作方式

1. **登記（track）**：在分析程式裡登記論文會用到的每個數字。

   ```python
   from stalecheck import track
   r = track("r_sleep_score", statistics.correlation(sleep, score))
   ```

   數值會存進 `.stalecheck/results.json`，並保留**歷史紀錄**：每個版本都記下產生它的 git commit 和 `檔案:行號`。這個檔案要一起 commit。

2. **標記（tag）**：在論文裡標記數字，寫成你希望印出來的樣子。

   | 格式 | 語法 |
   |------|------|
   | LaTeX | `\sv{r_sleep_score}{0.699}`，並定義 `\newcommand{\sv}[2]{#2}` |
   | Markdown | `0.699<!--sv:r_sleep_score-->` |

3. **檢查（check）**：執行 `stalecheck check paper.tex`。有過期數字時 exit code 為 1，所以可以用在 pre-commit hook 或 CI。

數字是**照論文寫出來的樣子**比對，而不是比對浮點數。`84.7\%` 代表「小數一位、百分比」，所以 0.8472 算相符，0.8476 不算。四捨五入採用論文慣用的 half-up（Python 的 `round` 不是）。自動修正會保留原本的寫法：`\%`、千分位、Unicode 負號，以及 APA 省略前導零的寫法（`.70 → .69`）。

| 狀態 | 意義 |
|------|------|
| `ok` | 文字與目前的值相符（以印出的精度比對） |
| `STALE` | 文字符合某個**舊值**，並列出改變它的那次執行 |
| `DIFF` | 文字不符合這個 key 曾有過的任何值（打錯字或手動改過） |
| `?KEY` | 標記用的 key 從未被登記 |
| `STALE?` | （`--scan`）**沒標記**的數字等於某個舊值，很可能已過期 |
| `tag?` | （`--scan`）沒標記的數字等於目前的值，建議加上標記 |

### 指令

```sh
stalecheck check paper.tex [--scan] [--json] [-v]
stalecheck fix paper.tex --write          # 改寫有標記的過期數字（不加 --write 只預覽）
stalecheck trace r_sleep_score paper.tex  # 查看歷史紀錄與論文中引用的位置
stalecheck list
stalecheck install-hook paper.tex         # 論文過期時阻擋 commit
```

`fix` 不會改動沒標記的數字，因為 Abstract 裡一個沒標記的 `0.85` 指的是 accuracy 還是別的東西，需要判斷。這正是 MCP server 的用途。

### MCP server（給 coding agent 使用）

`stalecheck-mcp` 把檢查功能提供給 agent（Claude Code、Claude Desktop、Cursor 等）。agent 改完分析程式後，可以自己確認論文有沒有因此出錯，並處理需要判斷的部分：判斷沒標記的數字代表什麼（`tag_number`），以及發現「strongly associated」這類措辭可能不再符合新的效果量。

| Tool | 功能 |
|------|------|
| `check_manuscript(path)` | 列出過期、不符、沒標記但過期的數字，並附上下文 |
| `fix_manuscript(path, dry_run=True)` | 預覽或套用有標記數字的改寫 |
| `trace_value(key)` | 完整歷史：數值、commit、程式行號、時間 |
| `list_values()` | 列出所有 key 與目前的值 |
| `tag_number(path, line, literal, key)` | 替沒標記的數字加上 key |

在 Claude Code 中設定：

```sh
claude mcp add -s user stalecheck -- /path/to/stalecheck/.venv/bin/stalecheck-mcp
```

### 安裝與測試

```sh
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest                          # 72 個測試
PYTHON=.venv/bin/python example/demo.sh   # 在暫存的 git repo 中跑完整 demo
```

### 限制

- 不掃描沒標記的**整數**（年份、章節編號、引用編號的誤報太多）。樣本數和自由度請加上標記。
- 只認得透過 `track()` 登記的數字。在文字中手算的數字（例如兩個登記值的差）需要另外 `track()`。
- 不支援 Word / Google Docs；請匯出成 Markdown，或用 LaTeX 管理數字。
