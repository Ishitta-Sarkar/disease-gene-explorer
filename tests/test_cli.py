"""Command-line explorer, including the offline fixture path."""

import json
import subprocess
import sys
from pathlib import Path

from disease_gene_explorer.open_targets import load_fixture
from disease_gene_explorer.plot import plot_association_scores

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "opentargets_sample.json"


def test_cli_offline_list_and_gene_search():
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "main.py"),
            "--input",
            str(FIXTURE),
            "--list",
            "--gene",
            "APP",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "Alzheimer disease [MONDO_0004975, 12918 direct associations]" in result.stdout
    assert "APP (ENSG00000142192)" in result.stdout
    assert "score 0.8147" in result.stdout


def test_cli_export_and_missing_input(tmp_path):
    export = tmp_path / "associations.tsv"
    meta = tmp_path / "meta.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "main.py"),
            "--input",
            str(FIXTURE),
            "--export",
            str(export),
            "--metadata-out",
            str(meta),
            "--disease",
            "Alzheimer disease",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    lines = export.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("disease_id\t")
    assert len(lines) == 7
    metadata = json.loads(meta.read_text(encoding="utf-8"))
    assert metadata["data_version"] == "26.09"
    assert "APP (ENSG00000142192)" in result.stdout

    missing = subprocess.run(
        [sys.executable, str(ROOT / "main.py"), "--input", str(tmp_path / "missing.json")],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert missing.returncode == 2


def test_plot_writes_png(tmp_path):
    records, _metadata = load_fixture(FIXTURE)
    output = plot_association_scores(records, tmp_path / "scores.png", top_n=3)
    assert output.is_file()
    assert output.stat().st_size > 1000
