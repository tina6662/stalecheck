import pytest

from stalecheck import store


@pytest.fixture
def make_store(tmp_path):
    """Build a results.json from {key: [v1, v2, ...]} (oldest first)."""

    def _make(values: dict[str, list[float]]):
        path = tmp_path / ".stalecheck" / "results.json"
        for key, versions in values.items():
            for i, v in enumerate(versions):
                store.record(key, v, store=path, source=f"analysis.py:{10 + i}", commit=f"c{i}")
        return path

    return _make


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.delenv(store.STORE_ENV, raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path
