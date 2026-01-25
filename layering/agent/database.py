"""Data loading and vectorization utilities for the layering service."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Iterable, List, Optional

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection as PGConnection

from . import schemas
from .constants import ACCORDS, ACCORD_INDEX, MATCH_SCORE_THRESHOLD, PERSISTENCE_MAP

try:  # pragma: no cover - optional dependency
    import Levenshtein  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    Levenshtein = None


load_dotenv()

DB_CONFIG: Dict[str, Any] = {
    "dbname": os.getenv("DB_NAME", "perfume_db"),
    "user": os.getenv("DB_USER", "scentence"),
    "password": os.getenv("DB_PASSWORD", "scentence"),
    "host": os.getenv("DB_HOST", "host.docker.internal"),
    "port": os.getenv("DB_PORT", "5432"),
}

def get_db_connection(
    db_config: Optional[Dict[str, Any]] = None,
) -> PGConnection:
    try:
        return psycopg2.connect(**(db_config or DB_CONFIG))
    except psycopg2.Error as exc:
        raise LayeringDataError(
            code="DB_CONNECTION_FAILED",
            message="DB 연결에 실패했습니다.",
            step="db_connect",
            retriable=False,
            details=str(exc),
        ) from exc
    except Exception as exc:
        raise LayeringDataError(
            code="DB_CONNECTION_FAILED",
            message="DB 연결에 실패했습니다.",
            step="db_connect",
            retriable=False,
            details=str(exc),
        ) from exc


def check_db_health(db_config: Optional[Dict[str, Any]] = None) -> bool:
    try:
        conn = get_db_connection(db_config)
    except LayeringDataError:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return True
    except psycopg2.Error:
        return False
    finally:
        conn.close()


class LayeringDataError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        step: str,
        retriable: bool = False,
        details: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.step = step
        self.retriable = retriable
        self.details = details


def _normalize_text(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9가-힣]+", " ", text.casefold())
    return " ".join(cleaned.split())


def _load_perfume_basics(conn) -> Dict[str, schemas.PerfumeBasic]:
    basics: Dict[str, schemas.PerfumeBasic] = {}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT perfume_id, perfume_name, perfume_brand
            FROM TB_PERFUME_BASIC_M
            """
        )
        for row in cur.fetchall():
            perfume_id = str(row.get("perfume_id") or "").strip()
            if not perfume_id:
                continue
            perfume_name = str(row.get("perfume_name") or perfume_id).strip() or perfume_id
            perfume_brand = str(row.get("perfume_brand") or "Unknown").strip() or "Unknown"
            basics[perfume_id] = schemas.PerfumeBasic(
                perfume_id=perfume_id,
                perfume_name=perfume_name,
                perfume_brand=perfume_brand,
            )
    return basics


def _load_perfume_accords(conn) -> Dict[str, Dict[str, float]]:
    accords: Dict[str, Dict[str, float]] = {}
    staged: Dict[str, Dict[str, Dict[str, float]]] = {}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT perfume_id, accord, ratio
            FROM TB_PERFUME_ACCORD_R
            """
        )
        for row in cur.fetchall():
            perfume_id = str(row.get("perfume_id") or "").strip()
            accord = str(row.get("accord") or "").strip()
            ratio_value = row.get("ratio")
            if not perfume_id or not accord:
                continue
            if accord not in ACCORDS:
                continue
            try:
                ratio = float(ratio_value)
            except (TypeError, ValueError):
                continue
            row_type = str(row.get("type") or "").strip().upper()
            buckets = staged.setdefault(perfume_id, {"base": {}, "all": {}})
            all_bucket = buckets["all"]
            all_bucket[accord] = all_bucket.get(accord, 0.0) + ratio
            if row_type == "BASE":
                base_bucket = buckets["base"]
                base_bucket[accord] = base_bucket.get(accord, 0.0) + ratio

    for perfume_id, buckets in staged.items():
        selected = buckets["base"] or buckets["all"]
        accords[perfume_id] = selected
    return accords


def _load_perfume_base_notes(conn) -> Dict[str, List[str]]:
    base_notes: Dict[str, List[str]] = {}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT perfume_id, note
            FROM TB_PERFUME_NOTES_M
            WHERE type = 'BASE'
            """
        )
        for row in cur.fetchall():
            perfume_id = str(row.get("perfume_id") or "").strip()
            note = str(row.get("note") or "").strip()
            if not perfume_id or not note:
                continue
            base_notes.setdefault(perfume_id, []).append(note)
    return base_notes


def _load_perfume_records(conn) -> List[schemas.PerfumeRecord]:
    basics = _load_perfume_basics(conn)
    accord_map = _load_perfume_accords(conn)
    base_notes = _load_perfume_base_notes(conn)

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
        db_config: Optional[Dict[str, str]] = None,
    ):
        self._db_config = db_config
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

    def _load_vectors(self) -> Dict[str, schemas.PerfumeVector]:
        try:
            conn = get_db_connection(self._db_config)
            try:
                records = _load_perfume_records(conn)
            finally:
                conn.close()
        except psycopg2.Error as exc:
            raise LayeringDataError(
                code="DB_QUERY_FAILED",
                message="DB 조회에 실패했습니다.",
                step="data_load",
                retriable=False,
                details=str(exc),
            ) from exc
        except LayeringDataError:
            raise
        except Exception as exc:
            raise LayeringDataError(
                code="DB_QUERY_FAILED",
                message="DB 조회에 실패했습니다.",
                step="data_load",
                retriable=False,
                details=str(exc),
            ) from exc
        if not records:
            raise LayeringDataError(
                code="DATASET_EMPTY",
                message="향수 데이터가 비어 있습니다.",
                step="data_load",
                retriable=False,
            )
        return {record.perfume.perfume_id: _vectorize(record) for record in records}

    def reload(self) -> None:
        self._vectors = self._load_vectors()
        self._name_index = self._build_name_index()

    def find_perfume_candidates(
        self,
        query: str,
        limit: int = 5,
        min_score: float | None = None,
    ) -> List[tuple[schemas.PerfumeVector, float, str]]:
        normalized_query = _normalize_text(query)
        if not normalized_query:
            return []

        min_fuzzy_score = min_score if min_score is not None else MATCH_SCORE_THRESHOLD

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
                continue
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
