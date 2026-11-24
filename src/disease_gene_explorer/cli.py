"""Command-line explorer for Open Targets disease–gene associations."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from disease_gene_explorer import __version__
from disease_gene_explorer.explorer import DiseaseGeneExplorer
from disease_gene_explorer.open_targets import OpenTargetsError, load_curated, load_fixture
from disease_gene_explorer.plot import plot_association_scores

TSV_FIELDS = [
    "disease_id",
    "disease",
    "gene_id",
    "gene",
    "approved_name",
    "biotype",
    "score",
    "datatype_scores",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Explore direct disease–gene associations from the Open Targets "
            "Platform (EFO disease ids, Ensembl gene ids, overall scores)."
        )
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--input",
        help="Offline fixture of GraphQL responses. Skips the network.",
    )
    parser.add_argument(
        "--disease-id",
        action="append",
        dest="disease_ids",
        help="EFO or MONDO disease id to query. Repeat to query several. "
        "Defaults to the five curated diseases.",
    )
    parser.add_argument("--disease", help="Disease name or id to summarize.")
    parser.add_argument("--gene", help="Gene symbol or Ensembl id to search.")
    parser.add_argument("--list", action="store_true", help="List loaded diseases.")
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Associations requested per disease (default: 10).",
    )
    parser.add_argument(
        "--cache-dir",
        default="cache/opentargets",
        help="Directory for cached API responses (default: cache/opentargets).",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore cached responses and query the Platform again.",
    )
    parser.add_argument("--export", help="Write the loaded associations to this TSV path.")
    parser.add_argument(
        "--metadata-out",
        help="Write query metadata (release, counts, accessions) as JSON.",
    )
    parser.add_argument("--plot", help="Write a bar chart of association scores to this path.")
    parser.add_argument(
        "--plot-top",
        type=int,
        default=8,
        help="Genes per disease in the figure (default: 8).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.top < 1 or args.plot_top < 1:
        print("Counts must be at least 1.", file=sys.stderr)
        return 2
    try:
        records, metadata = _load(args)
    except OpenTargetsError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    explorer = DiseaseGeneExplorer(records, metadata)
    if args.export:
        _export_tsv(records, args.export)
        print(f"Wrote {args.export}")
    if args.metadata_out:
        _write_json(metadata, args.metadata_out)
        print(f"Wrote {args.metadata_out}")
    if args.plot:
        plot_association_scores(records, args.plot, top_n=args.plot_top)
        print(f"Wrote {args.plot}")

    explicit = any([args.list, args.disease, args.gene, args.export, args.metadata_out, args.plot])
    if args.list or not explicit:
        _print_diseases(explorer)
    if args.disease or not explicit:
        disease = args.disease or _default_disease(explorer)
        print()
        print(explorer.summarize_disease(disease))
    if args.gene or not explicit:
        gene = args.gene or "APOE"
        print()
        print(f"Gene search: {gene}")
        print("-" * 30)
        print(_format_gene_hits(explorer.search_gene(gene)))
    return 0


def _load(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if args.input:
        return load_fixture(args.input)
    return load_curated(
        args.disease_ids,
        cache_dir=args.cache_dir,
        size=args.top,
        refresh=args.refresh,
    )


def _default_disease(explorer: DiseaseGeneExplorer) -> str:
    diseases = explorer.get_all_diseases()
    if not diseases:
        return "type 2 diabetes mellitus"
    for name in diseases:
        if name.casefold() == "type 2 diabetes mellitus":
            return name
    return diseases[0]


def _print_diseases(explorer: DiseaseGeneExplorer) -> None:
    print("Disease–gene explorer")
    version = explorer.metadata.get("data_version")
    if version:
        print(f"Open Targets data release: {version}")
    print("Diseases:")
    for name in explorer.get_all_diseases():
        rows = explorer.get_genes_by_disease(name)
        disease_id = rows[0]["disease_id"] if rows else ""
        info = explorer.metadata.get("diseases", {}).get(disease_id, {})
        count = info.get("association_count")
        count_text = f", {count} direct associations" if count is not None else ""
        print(f"- {name} [{disease_id}{count_text}]")


def _format_gene_hits(records: list[dict[str, Any]]) -> str:
    if not records:
        return "No associations in the loaded set."
    lines = []
    for record in records:
        lines.append(
            f"{record['gene']} ({record['gene_id']}) - "
            f"{record['disease']} ({record['disease_id']}), score {record['score']:.4f}"
        )
        lines.append(f"  {record['approved_name']}")
    return "\n".join(lines)


def _export_tsv(records: list[dict[str, Any]], path: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TSV_FIELDS, delimiter="\t")
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "disease_id": record["disease_id"],
                    "disease": record["disease"],
                    "gene_id": record["gene_id"],
                    "gene": record["gene"],
                    "approved_name": record["approved_name"],
                    "biotype": record["biotype"],
                    "score": format(record["score"], ".16g"),
                    "datatype_scores": json.dumps(
                        record["datatype_scores"],
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                }
            )


def _write_json(payload: dict[str, Any], path: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
