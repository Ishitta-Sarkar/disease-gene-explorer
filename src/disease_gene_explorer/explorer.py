"""In-memory search over disease–gene association records."""

from __future__ import annotations

from typing import Any


class DiseaseGeneExplorer:
    """Search association records loaded from the Open Targets Platform.

    Each record has ``disease``, ``disease_id``, ``gene``, ``gene_id``,
    ``approved_name``, ``biotype``, ``score``, and ``datatype_scores``.
    """

    def __init__(
        self,
        records: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.records = list(records)
        self.metadata = metadata or {}

    def get_all_diseases(self) -> list[str]:
        return sorted({record["disease"] for record in self.records}, key=str.casefold)

    def get_genes_by_disease(self, disease_name: str) -> list[dict[str, Any]]:
        matches = [record for record in self.records if _matches_disease(record, disease_name)]
        return sorted(matches, key=lambda record: (-record["score"], record["gene"]))

    def search_gene(self, gene_name: str) -> list[dict[str, Any]]:
        folded = gene_name.strip().casefold()
        matches = [
            record
            for record in self.records
            if record["gene"].casefold() == folded or record["gene_id"].casefold() == folded
        ]
        return sorted(
            matches,
            key=lambda record: (-record["score"], record["disease"], record["gene"]),
        )

    def summarize_disease(self, disease_name: str) -> str:
        genes = self.get_genes_by_disease(disease_name)
        if not genes:
            return f"No records found for {disease_name}."

        disease = genes[0]["disease"]
        disease_id = genes[0]["disease_id"]
        info = self.metadata.get("diseases", {}).get(disease_id, {})
        version = self.metadata.get("data_version")
        count = info.get("association_count")

        lines = [f"Disease: {disease} ({disease_id})"]
        if version:
            lines.append(f"Open Targets data release: {version}")
        if count is None:
            lines.append(f"Associations shown: {len(genes)}, ordered by overall score.")
        else:
            lines.append(
                f"Direct associations: showing {len(genes)} of {count}, ordered by overall score."
            )
        lines.append("Scores are printed to 4 decimal places.")
        lines.append("")
        for record in genes:
            lines.append(f"{record['gene']} ({record['gene_id']})  score {record['score']:.4f}")
            lines.append(f"  {record['approved_name']}")
            leading = _leading_datatype(record)
            if leading is not None:
                name, score = leading
                lines.append(f"  leading datatype: {name} ({score:.4f})")
        return "\n".join(lines)


def _matches_disease(record: dict[str, Any], query: str) -> bool:
    folded = query.strip().casefold()
    return record["disease"].casefold() == folded or record["disease_id"].casefold() == folded


def _leading_datatype(record: dict[str, Any]) -> tuple[str, float] | None:
    scores = record.get("datatype_scores") or {}
    if not scores:
        return None
    name, score = max(scores.items(), key=lambda item: (item[1], item[0]))
    return name, score
