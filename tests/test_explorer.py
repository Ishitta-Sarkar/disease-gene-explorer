"""Explorer behaviour on the offline fixture."""

from pathlib import Path

from disease_gene_explorer.explorer import DiseaseGeneExplorer
from disease_gene_explorer.open_targets import load_fixture

FIXTURE = Path("tests/fixtures/opentargets_sample.json")


def _explorer():
    records, metadata = load_fixture(FIXTURE)
    return DiseaseGeneExplorer(records, metadata)


def test_diseases_and_gene_lookup():
    explorer = _explorer()
    assert explorer.get_all_diseases() == [
        "Alzheimer disease",
        "type 2 diabetes mellitus",
    ]
    genes = explorer.get_genes_by_disease("type 2 diabetes mellitus")
    assert [row["gene"] for row in genes] == ["KCNJ11", "ABCC8", "GCK"]
    by_id = explorer.get_genes_by_disease("mondo_0004975")
    assert [row["gene"] for row in by_id] == ["APP", "ABCA7", "GRIN1"]
    assert explorer.get_genes_by_disease("malaria") == []


def test_search_gene_by_symbol_and_ensembl_id():
    explorer = _explorer()
    by_symbol = explorer.search_gene("app")
    assert len(by_symbol) == 1
    assert by_symbol[0]["disease_id"] == "MONDO_0004975"
    assert by_symbol[0]["approved_name"] == "amyloid beta precursor protein"
    by_id = explorer.search_gene("ensg00000187486")
    assert by_id[0]["gene"] == "KCNJ11"
    assert explorer.search_gene("APOE") == []


def test_summary_includes_ids_score_and_count():
    explorer = _explorer()
    summary = explorer.summarize_disease("MONDO_0005148")
    assert "type 2 diabetes mellitus (MONDO_0005148)" in summary
    assert "Open Targets data release: 26.09" in summary
    assert "showing 3 of 10206" in summary
    assert "KCNJ11 (ENSG00000187486)  score 0.8772" in summary
    assert "leading datatype: clinical (0.9985)" in summary
    assert explorer.summarize_disease("unknown").startswith("No records found")
