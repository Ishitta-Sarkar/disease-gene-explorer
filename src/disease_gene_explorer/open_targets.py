"""Client for Open Targets Platform disease–target associations.

Responses are cached as JSON. Tests and the offline explorer read a small
fixture of unmodified GraphQL ``data`` objects instead of calling the API.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from disease_gene_explorer.diseases import CURATED_DISEASES

API_URL = "https://api.platform.opentargets.org/api/v4/graphql"
CACHE_VERSION = 1
USER_AGENT = "disease-gene-explorer/0.2 (+https://github.com/Ishitta-Sarkar/disease-gene-explorer)"
_DISEASE_ID = re.compile(r"[A-Za-z]+_[A-Za-z0-9]+")

ASSOCIATION_QUERY = """
query DiseaseAssociations($efoId: String!, $size: Int!) {
  meta {
    apiVersion { x y z suffix }
    dataVersion { year month iteration }
  }
  disease(efoId: $efoId) {
    id
    name
    description
    dbXRefs
    associatedTargets(
      page: {index: 0, size: $size}
      enableIndirect: false
      orderByScore: "score desc"
    ) {
      count
      rows {
        score
        datatypeScores { id score }
        target {
          id
          approvedSymbol
          approvedName
          biotype
        }
      }
    }
  }
}
""".strip()


class OpenTargetsError(Exception):
    """The Platform request failed or the response could not be parsed."""


def normalize_disease_id(disease_id: str) -> str:
    """Accept ``MONDO_0005148`` and ``EFO:0003884`` and return the API form."""
    cleaned = disease_id.strip().replace(":", "_")
    if not _DISEASE_ID.fullmatch(cleaned):
        raise OpenTargetsError(
            "Disease id must look like an EFO or MONDO accession, for example MONDO_0005148."
        )
    return cleaned


def data_version_label(meta: dict[str, Any]) -> str | None:
    version = meta.get("dataVersion") or {}
    year = version.get("year")
    month = version.get("month")
    if not year or not month:
        return None
    label = f"{year}.{month}"
    iteration = version.get("iteration")
    if iteration:
        label = f"{label}.{iteration}"
    return label


def api_version_label(meta: dict[str, Any]) -> str | None:
    version = meta.get("apiVersion") or {}
    if not all(version.get(part) for part in ("x", "y", "z")):
        return None
    label = f"{version['x']}.{version['y']}.{version['z']}"
    if version.get("suffix"):
        label = f"{label}-{version['suffix']}"
    return label


def _as_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OpenTargetsError(f"{field} is missing from the Platform response.")
    if isinstance(value, float) and not value.is_integer():
        raise OpenTargetsError(f"{field} is not a whole number.")
    return int(value)


def parse_association_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Turn one GraphQL ``data`` object into association records."""
    disease = payload.get("disease")
    if not disease:
        raise OpenTargetsError("The Platform did not return a disease for that id.")
    associations = disease.get("associatedTargets") or {}
    rows = associations.get("rows") or []
    meta = payload.get("meta") or {}
    records: list[dict[str, Any]] = []
    for row in rows:
        target = row.get("target") or {}
        datatype_scores = {
            component["id"]: component["score"]
            for component in row.get("datatypeScores") or []
            if "id" in component and "score" in component
        }
        records.append(
            {
                "disease_id": disease["id"],
                "disease": disease["name"],
                "gene_id": target["id"],
                "gene": target["approvedSymbol"],
                "approved_name": target["approvedName"],
                "biotype": target.get("biotype"),
                "score": row["score"],
                "datatype_scores": datatype_scores,
            }
        )
    return {
        "disease_id": disease["id"],
        "disease": disease["name"],
        "description": disease.get("description"),
        "db_xrefs": list(disease.get("dbXRefs") or []),
        "association_count": _as_int(associations.get("count"), "Association count"),
        "data_version": data_version_label(meta),
        "api_version": api_version_label(meta),
        "records": records,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def cache_file(cache_dir: Path, disease_id: str, size: int) -> Path:
    safe = normalize_disease_id(disease_id)
    return Path(cache_dir) / f"{safe}.size{size}.direct.json"


class OpenTargetsClient:
    """Fetch direct disease–target associations, using a JSON cache."""

    def __init__(
        self,
        cache_dir: str | Path,
        url: str = API_URL,
        timeout: float = 60,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.url = url
        self.timeout = timeout

    def fetch_disease(
        self,
        disease_id: str,
        size: int = 10,
        refresh: bool = False,
    ) -> dict[str, Any]:
        disease_id = normalize_disease_id(disease_id)
        if size < 1:
            raise OpenTargetsError("Page size must be at least 1.")
        path = cache_file(self.cache_dir, disease_id, size)
        if not refresh:
            cached = self._read_cache(path)
            if cached is not None:
                parsed = parse_association_payload(cached["data"])
                parsed["fetched_at"] = cached.get("fetched_at")
                parsed["from_cache"] = True
                return parsed

        variables = {"efoId": disease_id, "size": size}
        data = self._post(ASSOCIATION_QUERY, variables)
        fetched_at = _utc_now()
        envelope = {
            "cache_version": CACHE_VERSION,
            "source": self.url,
            "fetched_at": fetched_at,
            "variables": variables,
            "enable_indirect": False,
            "order_by_score": "score desc",
            "data": data,
        }
        self._write_cache(path, envelope)
        parsed = parse_association_payload(data)
        parsed["fetched_at"] = fetched_at
        parsed["from_cache"] = False
        return parsed

    def _post(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise OpenTargetsError(f"Open Targets HTTP {exc.code}: {detail or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise OpenTargetsError(f"Open Targets request failed: {exc.reason}") from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OpenTargetsError("Open Targets returned invalid JSON.") from exc
        if payload.get("errors"):
            message = payload["errors"][0].get("message", "GraphQL error")
            raise OpenTargetsError(message)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise OpenTargetsError("Open Targets returned an empty data object.")
        return data

    def _read_cache(self, path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        if envelope.get("cache_version") != CACHE_VERSION:
            return None
        if not isinstance(envelope.get("data"), dict):
            return None
        return envelope

    def _write_cache(self, path: Path, envelope: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")


def _metadata_from_parsed(
    parsed_rows: list[dict[str, Any]],
    *,
    source: str,
    page_size: int | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    diseases: dict[str, Any] = {}
    data_version = None
    api_version = None
    for parsed in parsed_rows:
        records.extend(parsed["records"])
        data_version = parsed.get("data_version") or data_version
        api_version = parsed.get("api_version") or api_version
        diseases[parsed["disease_id"]] = {
            "name": parsed["disease"],
            "description": parsed.get("description"),
            "db_xrefs": parsed.get("db_xrefs") or [],
            "association_count": parsed["association_count"],
            "returned": len(parsed["records"]),
            "fetched_at": parsed.get("fetched_at"),
            "from_cache": parsed.get("from_cache"),
        }
    metadata = {
        "source": source,
        "data_version": data_version,
        "api_version": api_version,
        "page_size": page_size,
        "enable_indirect": False,
        "order_by_score": "score desc",
        "diseases": diseases,
    }
    return records, metadata


def load_curated(
    disease_ids: list[str] | None = None,
    *,
    cache_dir: str | Path,
    size: int = 10,
    refresh: bool = False,
    client: OpenTargetsClient | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load direct associations for the curated diseases, or for ``disease_ids``."""
    ids = disease_ids or [disease.disease_id for disease in CURATED_DISEASES]
    client = client or OpenTargetsClient(cache_dir)
    parsed_rows = [
        client.fetch_disease(disease_id, size=size, refresh=refresh) for disease_id in ids
    ]
    return _metadata_from_parsed(parsed_rows, source=client.url, page_size=size)


def load_fixture(path: str | Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load associations from a fixture of GraphQL ``data`` objects."""
    fixture_path = Path(path)
    try:
        text = fixture_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise OpenTargetsError(f"Could not read {fixture_path}: {exc.strerror}") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OpenTargetsError(f"{fixture_path} is not valid JSON.") from exc
    responses = payload.get("responses")
    if not isinstance(responses, list) or not responses:
        raise OpenTargetsError(f"{fixture_path} does not contain GraphQL responses.")
    parsed_rows = [parse_association_payload(item["data"]) for item in responses]
    records, metadata = _metadata_from_parsed(
        parsed_rows,
        source=payload.get("source", API_URL),
        page_size=payload.get("page_size"),
    )
    metadata["fixture"] = str(fixture_path)
    return records, metadata
