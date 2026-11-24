"""Parser, cache, and client tests. Network calls are replaced with the fixture."""

import json
import urllib.request
from pathlib import Path

import pytest

from disease_gene_explorer.open_targets import (
    CACHE_VERSION,
    OpenTargetsClient,
    OpenTargetsError,
    load_fixture,
    normalize_disease_id,
    parse_association_payload,
)

FIXTURE = Path("tests/fixtures/opentargets_sample.json")


class _Response:
    def __init__(self, payload: dict):
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _fixture_payload():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_normalize_disease_id_accepts_colon_form():
    assert normalize_disease_id(" efo:0003884 ") == "efo_0003884"
    assert normalize_disease_id("MONDO_0005148") == "MONDO_0005148"


def test_normalize_disease_id_rejects_free_text():
    with pytest.raises(OpenTargetsError):
        normalize_disease_id("type 2 diabetes")


def test_fixture_top_genes_and_release():
    records, metadata = load_fixture(FIXTURE)
    assert metadata["data_version"] == "26.09"
    assert metadata["api_version"] == "26.9.0"
    assert metadata["enable_indirect"] is False
    assert metadata["page_size"] == 3

    t2d = [row for row in records if row["disease_id"] == "MONDO_0005148"]
    alz = [row for row in records if row["disease_id"] == "MONDO_0004975"]
    assert [row["gene"] for row in t2d] == ["KCNJ11", "ABCC8", "GCK"]
    assert t2d[0]["gene_id"] == "ENSG00000187486"
    assert t2d[0]["score"] == 0.8772147341544883
    assert t2d[0]["datatype_scores"]["clinical"] == 0.9984847978522379
    assert [row["gene"] for row in alz] == ["APP", "ABCA7", "GRIN1"]
    assert alz[0]["gene_id"] == "ENSG00000142192"
    assert metadata["diseases"]["MONDO_0005148"]["association_count"] == 10206
    assert metadata["diseases"]["MONDO_0004975"]["association_count"] == 12918
    assert "DOID:9352" in metadata["diseases"]["MONDO_0005148"]["db_xrefs"]


def test_parse_missing_disease():
    with pytest.raises(OpenTargetsError):
        parse_association_payload({"disease": None, "meta": {}})


def test_fetch_uses_cache_and_refresh(tmp_path, monkeypatch):
    payload = _fixture_payload()["responses"][0]
    calls = []

    def fake_urlopen(request, timeout=0):
        calls.append(json.loads(request.data.decode("utf-8")))
        return _Response(payload)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = OpenTargetsClient(tmp_path)
    first = client.fetch_disease("MONDO_0005148", size=3)
    assert first["from_cache"] is False
    assert first["records"][0]["gene"] == "KCNJ11"
    assert calls[0]["variables"] == {"efoId": "MONDO_0005148", "size": 3}
    assert "enableIndirect: false" in calls[0]["query"]

    second = client.fetch_disease("MONDO_0005148", size=3)
    assert second["from_cache"] is True
    assert second["records"][0]["score"] == first["records"][0]["score"]
    assert len(calls) == 1

    client.fetch_disease("MONDO:0005148", size=3, refresh=True)
    assert len(calls) == 2
    cache_path = tmp_path / "MONDO_0005148.size3.direct.json"
    envelope = json.loads(cache_path.read_text(encoding="utf-8"))
    assert envelope["cache_version"] == CACHE_VERSION
    assert envelope["enable_indirect"] is False


def test_graphql_error_is_raised(tmp_path, monkeypatch):
    def fake_urlopen(request, timeout=0):
        return _Response({"errors": [{"message": "Unknown disease id"}], "data": None})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = OpenTargetsClient(tmp_path)
    with pytest.raises(OpenTargetsError, match="Unknown disease id"):
        client.fetch_disease("MONDO_0000000", size=1, refresh=True)


def test_stale_cache_is_ignored(tmp_path, monkeypatch):
    payload = _fixture_payload()["responses"][0]
    cache_path = tmp_path / "MONDO_0005148.size3.direct.json"
    cache_path.write_text(
        json.dumps({"cache_version": 0, "data": payload["data"]}) + "\n",
        encoding="utf-8",
    )

    def fake_urlopen(request, timeout=0):
        return _Response(payload)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    parsed = OpenTargetsClient(tmp_path).fetch_disease("MONDO_0005148", size=3)
    assert parsed["from_cache"] is False
    assert parsed["records"][0]["gene_id"] == "ENSG00000187486"
