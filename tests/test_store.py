import math
import subprocess

import pytest

from stalecheck import store, track


def test_record_appends_only_on_change(tmp_path):
    path = tmp_path / "r.json"
    assert store.record("acc", 0.8, store=path)
    assert not store.record("acc", 0.8, store=path)
    assert store.record("acc", 0.9, store=path)
    assert [e["value"] for e in store.load(path)["acc"]] == [0.8, 0.9]


@pytest.mark.parametrize("key", ["", "has space", "a/b", "ünïcode"])
def test_record_rejects_bad_keys(tmp_path, key):
    with pytest.raises(ValueError):
        store.record(key, 1.0, store=tmp_path / "r.json")


@pytest.mark.parametrize("value, exc", [(True, TypeError), ("0.8", TypeError), (math.nan, ValueError),
                                        (math.inf, ValueError)])
def test_record_rejects_bad_values(tmp_path, value, exc):
    with pytest.raises(exc):
        store.record("k", value, store=tmp_path / "r.json")


def test_load_missing_store_is_empty(tmp_path):
    assert store.load(tmp_path / "nope.json") == {}


def test_find_store_walks_up(isolated):
    (isolated / ".stalecheck").mkdir()
    deep = isolated / "paper" / "sections"
    deep.mkdir(parents=True)
    assert store.find_store(deep) == isolated / ".stalecheck" / "results.json"


def test_find_store_env_wins(isolated, monkeypatch):
    monkeypatch.setenv(store.STORE_ENV, str(isolated / "custom.json"))
    assert store.find_store() == isolated / "custom.json"


def test_find_store_defaults_to_start(isolated):
    assert store.find_store() == isolated / ".stalecheck" / "results.json"


def test_track_returns_value_and_records_source(isolated):
    assert track("n", 128) == 128
    entry = store.load(isolated / ".stalecheck" / "results.json")["n"][0]
    assert entry["value"] == 128
    assert entry["source"].startswith("test_store.py:")


def test_track_records_git_commit(isolated):
    run = lambda *a: subprocess.run(["git", *a], cwd=isolated, check=True, capture_output=True)
    run("init", "-q")
    run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "x")
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=isolated,
                         capture_output=True, text=True).stdout.strip()
    assert store.git_commit(isolated) == sha
    # A committed store being rewritten by track() must not count as dirty...
    (isolated / ".stalecheck").mkdir()
    (isolated / ".stalecheck" / "results.json").write_text("{}")
    run("add", ".")
    run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "store")
    sha = store.git_commit(isolated)
    (isolated / ".stalecheck" / "results.json").write_text('{"x": []}')
    (isolated / "sub").mkdir()
    assert store.git_commit(isolated / "sub") == sha
    # ...but any other tracked change does, even outside the caller's directory.
    (isolated / "f.txt").write_text("a")
    run("add", "f.txt")
    assert store.git_commit(isolated / "sub") == f"{sha}-dirty"


def test_git_commit_outside_repo(tmp_path):
    assert store.git_commit(tmp_path) is None
