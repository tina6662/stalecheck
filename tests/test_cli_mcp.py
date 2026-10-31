import asyncio
import json

from stalecheck import cli, mcp_server


def setup(make_store, tmp_path):
    store_path = make_store({"acc": [0.847, 0.851]})
    paper = tmp_path / "paper.md"
    paper.write_text("Intro\nAccuracy 84.7%<!--sv:acc-->.\n")
    return store_path, paper


def test_check_exit_codes(make_store, tmp_path, capsys):
    store_path, paper = setup(make_store, tmp_path)
    assert cli.main(["--store", str(store_path), "check", str(paper)]) == 1
    assert "84.7% -> 85.1%" in capsys.readouterr().out
    assert cli.main(["--store", str(store_path), "fix", "--write", str(paper)]) == 0
    assert cli.main(["--store", str(store_path), "check", str(paper)]) == 0


def test_check_finds_store_from_manuscript_dir(make_store, tmp_path, isolated):
    _, paper = setup(make_store, tmp_path)
    assert cli.main(["check", str(paper)]) == 1


def test_check_json(make_store, tmp_path, capsys):
    store_path, paper = setup(make_store, tmp_path)
    cli.main(["--store", str(store_path), "check", "--json", str(paper)])
    (f,) = json.loads(capsys.readouterr().out)
    assert f["kind"] == "stale" and f["line"] == 2


def test_trace_and_list(make_store, tmp_path, capsys):
    store_path, paper = setup(make_store, tmp_path)
    assert cli.main(["--store", str(store_path), "trace", "acc", str(paper)]) == 0
    out = capsys.readouterr().out
    assert "0.851" in out and f"cited at {paper}:2" in out
    assert cli.main(["--store", str(store_path), "trace", "nope"]) == 1
    cli.main(["--store", str(store_path), "list"])
    assert "2 versions" in capsys.readouterr().out


def test_install_hook_respects_existing_hook(isolated, capsys):
    hooks = isolated / ".git" / "hooks"
    hooks.mkdir(parents=True)
    assert cli.main(["install-hook", "paper.md"]) == 0
    assert "stalecheck check paper.md" in (hooks / "pre-commit").read_text()
    (hooks / "pre-commit").write_text("#!/bin/sh\nmake lint\n")
    assert cli.main(["install-hook", "paper.md"]) == 1
    assert "make lint" in (hooks / "pre-commit").read_text()


def call(name, **args):
    result = asyncio.run(mcp_server.server.call_tool(name, args))
    assert not result.is_error, result.content
    return json.loads(result.content[0].text)


def test_mcp_tools_registered():
    names = {t.name for t in asyncio.run(mcp_server.server.list_tools())}
    assert names == {"check_manuscript", "fix_manuscript", "trace_value", "list_values", "tag_number"}


def test_mcp_check_fix_roundtrip(make_store, tmp_path):
    store_path, paper = setup(make_store, tmp_path)
    res = call("check_manuscript", path=str(paper), store_path=str(store_path))
    assert res["needs_attention"] and res["problems"][0]["context"].endswith("Accuracy 84.7%<!--sv:acc-->.")
    preview = call("fix_manuscript", path=str(paper), store_path=str(store_path))
    assert preview["changes"] == [{"line": 2, "old": "84.7%", "new": "85.1%", "key": "acc"}]
    assert "84.7%" in paper.read_text()
    call("fix_manuscript", path=str(paper), dry_run=False, store_path=str(store_path))
    assert not call("check_manuscript", path=str(paper), store_path=str(store_path))["needs_attention"]


def test_mcp_tag_number(make_store, tmp_path):
    store_path = make_store({"acc": [0.851]})
    paper = tmp_path / "paper.tex"
    paper.write_text("We got 85.1\\% accuracy.\n")
    assert call("tag_number", path=str(paper), line=1, literal="85.1\\%", key="acc")["ok"]
    assert paper.read_text() == "We got \\sv{acc}{85.1\\%} accuracy.\n"
    assert not call("tag_number", path=str(paper), line=1, literal="99", key="acc")["ok"]
    res = call("check_manuscript", path=str(paper), store_path=str(store_path))
    assert res["up_to_date"] == 1 and not res["problems"]
