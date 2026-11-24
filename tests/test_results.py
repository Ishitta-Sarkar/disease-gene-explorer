"""Checks on the committed Open Targets 26.09 snapshot used in the README."""

import csv
import json
from pathlib import Path

TSV = Path("results/top_associations.tsv")
METADATA = Path("results/query_metadata.json")
FIGURE = Path("figures/top_association_scores.png")

TOP_GENES = {
    "MONDO_0005148": "KCNJ11",
    "MONDO_0004975": "APP",
    "MONDO_0005180": "GBA1",
    "MONDO_0005300": "PKD2",
    "MONDO_0004976": "SOD1",
}
COUNTS = {
    "MONDO_0005148": 10206,
    "MONDO_0004975": 12918,
    "MONDO_0005180": 8815,
    "MONDO_0005300": 4938,
    "MONDO_0004976": 6088,
}


def test_committed_associations_match_release_query():
    rows = list(csv.DictReader(TSV.open(encoding="utf-8"), delimiter="\t"))
    assert len(rows) == 50
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["disease_id"], []).append(row)
    assert list(grouped) == list(TOP_GENES)
    for disease_id, group in grouped.items():
        assert len(group) == 10
        assert group[0]["gene"] == TOP_GENES[disease_id]
        assert group[0]["gene_id"].startswith("ENSG")
        scores = [float(row["score"]) for row in group]
        assert scores == sorted(scores, reverse=True)
    assert grouped["MONDO_0005148"][0]["gene_id"] == "ENSG00000187486"
    assert grouped["MONDO_0005148"][0]["score"] == "0.8772147341544883"
    assert grouped["MONDO_0004976"][0]["gene_id"] == "ENSG00000142168"

    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    assert metadata["source"] == "https://api.platform.opentargets.org/api/v4/graphql"
    assert metadata["data_version"] == "26.09"
    assert metadata["api_version"] == "26.9.0"
    assert metadata["page_size"] == 10
    assert metadata["enable_indirect"] is False
    assert metadata["order_by_score"] == "score desc"
    for disease_id, count in COUNTS.items():
        info = metadata["diseases"][disease_id]
        assert info["association_count"] == count
        assert info["returned"] == 10
        assert info["from_cache"] is False
        assert info["fetched_at"].startswith("2026-11-24T")
    assert "EFO:0003884" in metadata["diseases"]["MONDO_0005300"]["db_xrefs"]
    assert FIGURE.is_file()
    assert FIGURE.stat().st_size > 10_000
