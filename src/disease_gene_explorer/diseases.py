"""Diseases queried by the explorer.

The identifiers below are the top ``mapIds`` hit for each query term on the
Open Targets Platform GraphQL API (data release 26.09, retrieved 24 November
2026). Each hit had search score 1.0. They are fixed here so later runs do not
depend on search ranking.

The GraphQL argument is named ``efoId``. For these five terms the Platform's
disease identifier is a MONDO accession inside the Experimental Factor
Ontology used by Open Targets. Chronic kidney disease also carries the
cross-reference ``EFO:0003884``.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CuratedDisease:
    disease_id: str
    query_term: str


CURATED_DISEASES: tuple[CuratedDisease, ...] = (
    CuratedDisease("MONDO_0005148", "type 2 diabetes mellitus"),
    CuratedDisease("MONDO_0004975", "Alzheimer disease"),
    CuratedDisease("MONDO_0005180", "Parkinson disease"),
    CuratedDisease("MONDO_0005300", "chronic kidney disease"),
    CuratedDisease("MONDO_0004976", "amyotrophic lateral sclerosis"),
)
