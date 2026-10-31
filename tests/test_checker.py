from stalecheck import checker, store


def kinds(findings):
    return [(f.kind, f.literal) for f in findings]


def test_ok_and_stale(make_store):
    data = store.load(make_store({"acc": [0.847, 0.851], "n": [120]}))
    text = "acc 84.7%<!--sv:acc--> with n=120<!--sv:n-->"
    acc, n = checker.check_text(text, data)
    assert (acc.kind, acc.expected, acc.old_value, acc.current_value) == ("stale", "85.1%", 0.847, 0.851)
    assert acc.changed_by["source"] == "analysis.py:11" and acc.changed_by["commit"] == "c1"
    assert n.kind == "ok"


def test_change_below_printed_precision_is_not_stale(make_store):
    data = store.load(make_store({"acc": [0.8471, 0.8474]}))
    assert kinds(checker.check_text("0.847<!--sv:acc-->", data)) == [("ok", "0.847")]


def test_stale_points_at_the_change_after_the_latest_match(make_store):
    # 0.80 -> 0.85 -> 0.80 -> 0.90: text "0.80" was last true at index 2, broken by index 3
    data = store.load(make_store({"acc": [0.80, 0.85, 0.80, 0.90]}))
    (f,) = checker.check_text("0.80<!--sv:acc-->", data)
    assert f.kind == "stale" and f.changed_by["commit"] == "c3"


def test_mismatch_and_unknown_key(make_store):
    data = store.load(make_store({"acc": [0.851]}))
    text = "84.0%<!--sv:acc--> and 1.0<!--sv:ghost-->"
    a, g = checker.check_text(text, data)
    assert (a.kind, a.expected) == ("mismatch", "85.1%")
    assert g.kind == "unknown_key"


def test_scan_untagged(make_store):
    data = store.load(make_store({"acc": [0.847, 0.851], "r": [-0.31]}))
    text = "Accuracy reached 84.7% and the correlation was -0.31; threshold 0.05."
    found = checker.check_text(text, data, scan=True)
    assert kinds(found) == [("untagged_stale", "84.7%"), ("untagged_current", "-0.31")]
    assert found[0].keys == ["acc"] and found[0].expected == "85.1%"


def test_scan_ambiguous_stale_has_no_suggestion(make_store):
    data = store.load(make_store({"a": [0.5, 0.6], "b": [0.5, 0.7]}))
    (f,) = checker.check_text("value 0.5 here", data, scan=True)
    assert f.kind == "untagged_stale" and f.keys == ["a", "b"] and f.expected is None


def test_fix_rewrites_only_tagged(make_store):
    data = store.load(make_store({"acc": [0.847, 0.851]}))
    text = "\\sv{acc}{84.7\\%} vs untagged 84.7\\%"
    new, fixed = checker.fix_text(text, data, latex=True)
    assert new == "\\sv{acc}{85.1\\%} vs untagged 84.7\\%"
    assert len(fixed) == 1
    assert checker.check_text(new, data, latex=True)[0].kind == "ok"


def test_fix_multiple_on_one_line_keeps_offsets(make_store):
    data = store.load(make_store({"a": [0.1, 0.123456], "b": [2.0, 22.5]}))
    new, _ = checker.fix_text("0.10<!--sv:a--> and 2.0<!--sv:b-->!", data)
    assert new == "0.12<!--sv:a--> and 22.5<!--sv:b-->!"


def test_fix_file_dry_run_does_not_write(make_store, tmp_path):
    data = store.load(make_store({"acc": [0.8, 0.9]}))
    p = tmp_path / "paper.md"
    p.write_text("0.8<!--sv:acc-->")
    assert len(checker.fix_file(p, data)) == 1
    assert p.read_text() == "0.8<!--sv:acc-->"
    checker.fix_file(p, data, write=True)
    assert p.read_text() == "0.9<!--sv:acc-->"


def test_usages(make_store, tmp_path):
    p = tmp_path / "paper.tex"
    p.write_text("a \\sv{acc}{0.8}\n\nb \\sv{acc}{80\\%}\n")
    assert [u["line"] for u in checker.usages([p], "acc")] == [1, 3]
