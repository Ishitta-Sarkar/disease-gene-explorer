# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog, and this project uses semantic versioning.

## [0.2.0] - 2026-11-24

### Changed

- Replaced the hand-curated `data/disease_genes.csv` with direct target–disease associations from the Open Targets Platform GraphQL API.
- Each disease record now carries the Platform disease identifier (an EFO-ontology id; a MONDO accession for the five curated terms) and each gene carries an Ensembl gene id, an approved symbol and name, an overall association score, and datatype scores.
- `DiseaseGeneExplorer.summarize_disease` reports those Platform fields.

### Added

- JSON cache for API responses under `cache/opentargets/` (not committed).
- Offline fixture `tests/fixtures/opentargets_sample.json` for the tests and for running the explorer without a network connection.
- Pinned `requirements.txt`, pytest suite, and GitHub Actions workflow (ruff and pytest).
- `CITATION.cff`.
- Results table and figure for the top direct associations in Platform release 26.09, queried on 24 November 2026.

## [0.1.0] - 2026-06-16

### Added

- Command-line explorer over a 10-row hand-curated disease–gene table.
