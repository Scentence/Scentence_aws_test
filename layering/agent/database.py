"""Data loading and vectorization utilities for the layering service."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from . import schemas
from .constants import ACCORDS, ACCORD_INDEX, BASE_NOTE_INDEXES, PERSISTENCE_MAP


DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "perfumes.json"


def _load_perfume_records(data_path: Path) -> List[schemas.PerfumeRecord]:
    with data_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    perfumes = []
    for item in payload.get("perfumes", []):
        perfume = schemas.PerfumeBasic(
            perfume_id=str(item["perfume_id"]),
            perfume_name=item["perfume_name"],
            perfume_brand=item["perfume_brand"],
        )
        accords = [
            schemas.PerfumeAccord(**accord_dict)
            for accord_dict in item.get("accords", [])
        ]
        perfumes.append(schemas.PerfumeRecord(perfume=perfume, accords=accords))
    return perfumes


def _vectorize(record: schemas.PerfumeRecord) -> schemas.PerfumeVector:
    vector = [0.0] * len(ACCORDS)
    for accord in record.accords:
        vector[ACCORD_INDEX[accord.accord]] = accord.ratio

    total_intensity = sum(vector)
    persistence_score = _persistence_score(vector)
    dominant = [
        ACCORDS[idx]
        for idx, value in enumerate(vector)
        if value > 5
    ]
    base_note_vector = [vector[idx] for idx in BASE_NOTE_INDEXES]
    return schemas.PerfumeVector(
        perfume_id=record.perfume.perfume_id,
        perfume_name=record.perfume.perfume_name,
        perfume_brand=record.perfume.perfume_brand,
        vector=vector,
        total_intensity=total_intensity,
        persistence_score=persistence_score,
        dominant_accords=dominant,
        base_note_vector=base_note_vector,
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

    def __init__(self, data_path: Optional[os.PathLike[str] | str] = None):
        resolved = self._resolve_path(data_path)
        if not resolved.exists():
            raise FileNotFoundError(f"Perfume data file not found: {resolved}")
        self._data_path = resolved
        self._vectors = self._load_vectors()

    def _resolve_path(self, supplied_path: Optional[os.PathLike[str] | str]) -> Path:
        if supplied_path:
            return Path(supplied_path)
        if env_path := os.getenv("LAYERING_DATA_PATH"):
            return Path(env_path)
        return DEFAULT_DATA_PATH

    def _load_vectors(self) -> Dict[str, schemas.PerfumeVector]:
        records = _load_perfume_records(self._data_path)
        return {record.perfume.perfume_id: _vectorize(record) for record in records}

    def reload(self) -> None:
        self._vectors = self._load_vectors()

    def get_perfume(self, perfume_id: str) -> schemas.PerfumeVector:
        try:
            return self._vectors[perfume_id]
        except KeyError as exc:
            raise KeyError(f"Perfume '{perfume_id}' not found") from exc

    def all_candidates(self, exclude_id: Optional[str] = None) -> Iterable[schemas.PerfumeVector]:
        for perfume_id, vector in self._vectors.items():
            if perfume_id == exclude_id:
                continue
            yield vector

    @property
    def count(self) -> int:
        return len(self._vectors)
