"""Data loading and vectorization utilities for the layering service."""

from __future__ import annotations

import csv
import os
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from . import schemas
from .constants import ACCORDS, ACCORD_INDEX, MATCH_SCORE_THRESHOLD, PERSISTENCE_MAP

try:  # pragma: no cover - optional dependency
    import Levenshtein
except ImportError:  # pragma: no cover
    Levenshtein = None


_env_db_root = os.getenv("LAYERING_DB_ROOT")
if _env_db_root:
    DEFAULT_DB_ROOT = Path(_env_db_root)
else:
    _parents = Path(__file__).resolve().parents
    _base_root = _parents[3] if len(_parents) > 3 else _parents[-1]
    DEFAULT_DB_ROOT = (
        _base_root / "scentence-db-init" / "postgres" / "RDB" / "scripts" / "perfume_db"
    )
DEFAULT_ACCORDS_PATH = DEFAULT_DB_ROOT / "routputs" / "TB_PERFUME_ACCORD_R.csv"
DEFAULT_NOTES_PATH = DEFAULT_DB_ROOT / "outputs" / "TB_PERFUME_NOTES_M.csv"
DEFAULT_BASIC_PATH = DEFAULT_DB_ROOT / "outputs" / "TB_PERFUME_BASIC_M.csv"


def _normalize_row(row: Dict[str, str]) -> Dict[str, str]:
    return {
        str(key).strip().upper(): (value or "").strip() for key, value in row.items()
    }


def _normalize_text(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9가-힣]+", " ", text.casefold())
    return " ".join(cleaned.split())


def _load_perfume_basics(data_path: Path) -> Dict[str, schemas.PerfumeBasic]:
    basics: Dict[str, schemas.PerfumeBasic] = {}
    with data_path.open("r", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            normalized = _normalize_row(row)
            perfume_id = normalized.get("PERFUME_ID", "")
            if not perfume_id:
                continue
            basics[perfume_id] = schemas.PerfumeBasic(
                perfume_id=perfume_id,
                perfume_name=normalized.get("PERFUME_NAME", perfume_id) or perfume_id,
                perfume_brand=normalized.get("PERFUME_BRAND", "Unknown") or "Unknown",
            )
    return basics


def _load_perfume_accords(data_path: Path) -> Dict[str, Dict[str, float]]:
    accords: Dict[str, Dict[str, float]] = {}
    with data_path.open("r", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = [name.strip().upper() for name in (reader.fieldnames or [])]
        has_type = "TYPE" in fieldnames
        if has_type:
            staged: Dict[str, Dict[str, Dict[str, float]]] = {}
            for row in reader:
                normalized = _normalize_row(row)
                perfume_id = normalized.get("PERFUME_ID", "")
                accord = normalized.get("ACCORD", "")
                ratio_value = normalized.get("RATIO", "")
                if not perfume_id or not accord:
                    continue
                if accord not in ACCORDS:
                    continue
                try:
                    ratio = float(ratio_value)
                except ValueError:
                    continue
                row_type = normalized.get("TYPE", "").upper()
                buckets = staged.setdefault(perfume_id, {"base": {}, "all": {}})
                all_bucket = buckets["all"]
                all_bucket[accord] = all_bucket.get(accord, 0.0) + ratio
                if row_type == "BASE":
                    base_bucket = buckets["base"]
                    base_bucket[accord] = base_bucket.get(accord, 0.0) + ratio
            for perfume_id, buckets in staged.items():
                selected = buckets["base"] or buckets["all"]
                accords[perfume_id] = selected
        else:
            for row in reader:
                normalized = _normalize_row(row)
                perfume_id = normalized.get("PERFUME_ID", "")
                accord = normalized.get("ACCORD", "")
                ratio_value = normalized.get("RATIO", "")
                if not perfume_id or not accord:
                    continue
                if accord not in ACCORDS:
                    continue
                try:
                    ratio = float(ratio_value)
                except ValueError:
                    continue
                perfume_entry = accords.setdefault(perfume_id, {})
                perfume_entry[accord] = perfume_entry.get(accord, 0.0) + ratio
    return accords


def _load_perfume_base_notes(data_path: Path) -> Dict[str, List[str]]:
    base_notes: Dict[str, List[str]] = {}
    with data_path.open("r", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            normalized = _normalize_row(row)
            row_type = normalized.get("TYPE", "").upper()
            if row_type != "BASE":
                continue
            perfume_id = normalized.get("PERFUME_ID", "")
            note = normalized.get("NOTE", "")
            if not perfume_id or not note:
                continue
            base_notes.setdefault(perfume_id, []).append(note)
    return base_notes


def _load_perfume_records(
    accord_path: Path,
    notes_path: Path,
    basic_path: Path,
) -> List[schemas.PerfumeRecord]:
    basics = _load_perfume_basics(basic_path)
    accord_map = _load_perfume_accords(accord_path)
    base_notes = _load_perfume_base_notes(notes_path)

    perfumes: List[schemas.PerfumeRecord] = []
    for perfume_id, accord_entries in accord_map.items():
        perfume = basics.get(perfume_id)
        if perfume is None:
            perfume = schemas.PerfumeBasic(
                perfume_id=perfume_id,
                perfume_name=perfume_id,
                perfume_brand="Unknown",
            )
        accords = [
            schemas.PerfumeAccord(accord=accord, ratio=ratio)
            for accord, ratio in accord_entries.items()
        ]
        notes = sorted(set(base_notes.get(perfume_id, [])))
        perfumes.append(
            schemas.PerfumeRecord(perfume=perfume, accords=accords, base_notes=notes)
        )
    return perfumes


def _vectorize(record: schemas.PerfumeRecord) -> schemas.PerfumeVector:
    vector = [0.0] * len(ACCORDS)
    for accord in record.accords:
        vector[ACCORD_INDEX[accord.accord]] = accord.ratio

    total_intensity = sum(vector)
    persistence_score = _persistence_score(vector)
    dominant = [ACCORDS[idx] for idx, value in enumerate(vector) if value > 5]
    return schemas.PerfumeVector(
        perfume_id=record.perfume.perfume_id,
        perfume_name=record.perfume.perfume_name,
        perfume_brand=record.perfume.perfume_brand,
        vector=vector,
        total_intensity=total_intensity,
        persistence_score=persistence_score,
        dominant_accords=dominant,
        base_notes=record.base_notes,
    )


def _persistence_score(vector: List[float]) -> float:
    numerator = 0.0
    denominator = 0.0
    for accord_name, value in zip(ACCORDS, vector):
        if value <= 0:
            continue
        weight = PERSISTENCE_MAP.get(accord_name, 0)
        numerator += value * weight
        denominator += value
    return numerator / denominator if denominator else 0.0


class PerfumeRepository:
    """In-memory cache of perfume vectors."""

    def __init__(
        self,
        data_root: Optional[os.PathLike[str] | str] = None,
        accord_path: Optional[os.PathLike[str] | str] = None,
        notes_path: Optional[os.PathLike[str] | str] = None,
        basic_path: Optional[os.PathLike[str] | str] = None,
    ):
        self._accord_path, self._notes_path, self._basic_path = self._resolve_paths(
            data_root,
            accord_path,
            notes_path,
            basic_path,
        )
        for path in (self._accord_path, self._notes_path, self._basic_path):
            if not path.exists():
                raise FileNotFoundError(f"Perfume data file not found: {path}")
        self._vectors = self._load_vectors()
        self._name_index = self._build_name_index()

    def _build_name_index(self) -> Dict[str, List[schemas.PerfumeVector]]:
        index: Dict[str, List[schemas.PerfumeVector]] = {}
        for perfume in self._vectors.values():
            candidates = [
                perfume.perfume_name,
                f"{perfume.perfume_brand} {perfume.perfume_name}",
                f"{perfume.perfume_name} {perfume.perfume_brand}",
            ]
            for candidate in candidates:
                normalized = _normalize_text(candidate)
                if not normalized:
                    continue
                index.setdefault(normalized, []).append(perfume)
        return index

    def _resolve_paths(
        self,
        data_root: Optional[os.PathLike[str] | str],
        accord_path: Optional[os.PathLike[str] | str],
        notes_path: Optional[os.PathLike[str] | str],
        basic_path: Optional[os.PathLike[str] | str],
    ) -> tuple[Path, Path, Path]:
        root = Path(data_root) if data_root else None
        if env_root := os.getenv("LAYERING_DB_ROOT"):
            root = Path(env_root)
        if root is None:
            root = DEFAULT_DB_ROOT

        resolved_accord = Path(accord_path) if accord_path else None
        resolved_notes = Path(notes_path) if notes_path else None
        resolved_basic = Path(basic_path) if basic_path else None

        if env_accord := os.getenv("LAYERING_ACCORDS_CSV"):
            resolved_accord = Path(env_accord)
        if env_notes := os.getenv("LAYERING_NOTES_CSV"):
            resolved_notes = Path(env_notes)
        if env_basic := os.getenv("LAYERING_BASIC_CSV"):
            resolved_basic = Path(env_basic)

        if resolved_accord is None:
            resolved_accord = root / "routputs" / "TB_PERFUME_ACCORD_R.csv"
        if resolved_notes is None:
            resolved_notes = root / "outputs" / "TB_PERFUME_NOTES_M.csv"
        if resolved_basic is None:
            resolved_basic = root / "outputs" / "TB_PERFUME_BASIC_M.csv"

        return resolved_accord, resolved_notes, resolved_basic

    def _load_vectors(self) -> Dict[str, schemas.PerfumeVector]:
        records = _load_perfume_records(
            self._accord_path,
            self._notes_path,
            self._basic_path,
        )
        return {record.perfume.perfume_id: _vectorize(record) for record in records}

    def reload(self) -> None:
        self._vectors = self._load_vectors()
        self._name_index = self._build_name_index()

    def find_perfume_candidates(
        self,
        query: str,
        limit: int = 5,
    ) -> List[tuple[schemas.PerfumeVector, float, str]]:
        normalized_query = _normalize_text(query)
        if not normalized_query:
            return []

        min_fuzzy_score = MATCH_SCORE_THRESHOLD

        matches: Dict[str, tuple[float, str]] = {}
        for key, perfumes in self._name_index.items():
            score = 0.0
            if normalized_query == key:
                score = 1.0
            elif (
                len(key) >= 3
                and len(normalized_query) >= 3
                and (normalized_query in key or key in normalized_query)
            ):
                score = 0.9
            elif Levenshtein is not None:
                score = Levenshtein.ratio(normalized_query, key)
                if score < min_fuzzy_score:
                    score = 0.0
            if score <= 0.0:
                continue
            for perfume in perfumes:
                current = matches.get(perfume.perfume_id, (0.0, ""))
                if score > current[0]:
                    matches[perfume.perfume_id] = (score, key)

        ranked = sorted(
            (
                (score, key, self._vectors[perfume_id])
                for perfume_id, (score, key) in matches.items()
                if perfume_id in self._vectors
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        return [(perfume, score, key) for score, key, perfume in ranked[:limit]]

    def get_perfume(self, perfume_id: str) -> schemas.PerfumeVector:
        try:
            return self._vectors[perfume_id]
        except KeyError as exc:
            raise KeyError(f"Perfume '{perfume_id}' not found") from exc

    def all_candidates(
        self, exclude_id: Optional[str] = None
    ) -> Iterable[schemas.PerfumeVector]:
        for perfume_id, vector in self._vectors.items():
            if perfume_id == exclude_id:
                continue
            yield vector

    @property
    def count(self) -> int:
        return len(self._vectors)
