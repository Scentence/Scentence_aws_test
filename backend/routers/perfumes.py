"""
향수 검색 API 라우터 (Re-created)
"""

import importlib
import os
from typing import Any

from pydantic import BaseModel

psycopg2: Any = importlib.import_module("psycopg2")
RealDictCursor: Any = importlib.import_module("psycopg2.extras").RealDictCursor
_fastapi: Any = importlib.import_module("fastapi")
APIRouter: Any = _fastapi.APIRouter
HTTPException: Any = _fastapi.HTTPException
Query: Any = _fastapi.Query

router = APIRouter(prefix="/perfumes", tags=["Perfumes"])

# ============================================================
# DB 연결
# ============================================================

def _get_env(key: str, default: str) -> str:
    return os.environ.get(key, default)

PERFUME_DB_PARAMS = {
    "dbname": "perfume_db",
    "user": _get_env("DB_USER", "scentence"),
    "password": _get_env("DB_PASSWORD", "scentence"),
    # Docker 내부 통신용: host.docker.internal 또는 서비스명 사용
    "host": _get_env("DB_HOST", "host.docker.internal"),
    "port": _get_env("DB_PORT", "5432"),
}

def get_perfume_db():
    try:
        conn = psycopg2.connect(
            **PERFUME_DB_PARAMS,
            cursor_factory=RealDictCursor,
        )
        return conn
    except Exception as e:
        print(f"❌ DB Connection Error: {e}")
        raise e


# ============================================================
# 모델
# ============================================================

class PerfumeSearchResult(BaseModel):
    perfume_id: int
    name: str
    brand: str
    image_url: str | None


class RatioItem(BaseModel):
    """Ratio 항목 (어코드/계절/상황)"""
    name: str
    ratio: int  # 0~100 정수 (정규화됨)


class PerfumeNotes(BaseModel):
    """향수 노트 (Top/Middle/Base)"""
    top: list[str]
    middle: list[str]
    base: list[str]


class PerfumeDetailResponse(BaseModel):
    """향수 상세 정보 응답"""
    perfume_id: int
    name: str
    brand: str
    image_url: str | None = None
    release_year: int | None = None
    concentration: str | None = None
    perfumer: str | None = None
    notes: PerfumeNotes
    accords: list[RatioItem]
    seasons: list[RatioItem]
    occasions: list[RatioItem]


# ============================================================
# API
# ============================================================

def normalize_ratio(ratio: float | None) -> int:
    if ratio is None:
        return 0
    if ratio <= 1.0:
        value = ratio * 100
    else:
        value = ratio
    return int(max(0, min(value, 100)))

@router.get("/search", response_model=list[PerfumeSearchResult])
def search_perfumes(q: str = Query(..., min_length=1, description="검색어")):
    """
    향수 검색 (이름/브랜드)

    - ILIKE 검색으로 부분 일치
    - 최대 20개 결과 반환
    """
    search_term = f"%{q}%"

    try:
        conn = get_perfume_db()
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        perfume_id,
                        perfume_name,
                        perfume_brand,
                        img_link
                    FROM tb_perfume_basic_m
                    WHERE perfume_name ILIKE %s
                       OR perfume_brand ILIKE %s
                    LIMIT 20
                """, (search_term, search_term))
                results = cur.fetchall()
        
        conn.close()

        return [
            PerfumeSearchResult(
                perfume_id=r["perfume_id"],
                name=r["perfume_name"],
                brand=r["perfume_brand"],
                image_url=r["img_link"],
            )
            for r in results
        ]

    except Exception as e:
        print(f"Error searching perfumes: {e}")
        return []


@router.get("/detail", response_model=PerfumeDetailResponse)
def get_perfume_detail(
    perfume_id: int = Query(..., description="향수 ID"),
):
    try:
        conn = get_perfume_db()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT perfume_id, perfume_name, perfume_brand, release_year,
                           concentration, perfumer, img_link
                    FROM tb_perfume_basic_m
                    WHERE perfume_id = %s;
                    """,
                    (perfume_id,),
                )
                basic = cur.fetchone()
                if not basic:
                    raise HTTPException(status_code=404, detail="Perfume not found")

                cur.execute(
                    """
                    SELECT note, type
                    FROM tb_perfume_notes_m
                    WHERE perfume_id = %s;
                    """,
                    (perfume_id,),
                )
                note_rows = cur.fetchall()

                cur.execute(
                    """
                    SELECT accord, ratio
                    FROM tb_perfume_accord_r
                    WHERE perfume_id = %s
                    ORDER BY ratio DESC NULLS LAST
                    LIMIT 5;
                    """,
                    (perfume_id,),
                )
                accord_rows = cur.fetchall()

                cur.execute(
                    """
                    SELECT season, ratio
                    FROM tb_perfume_season_r
                    WHERE perfume_id = %s
                    ORDER BY ratio DESC NULLS LAST
                    LIMIT 5;
                    """,
                    (perfume_id,),
                )
                season_rows = cur.fetchall()

                cur.execute(
                    """
                    SELECT occasion, ratio
                    FROM tb_perfume_oca_r
                    WHERE perfume_id = %s
                    ORDER BY ratio DESC NULLS LAST
                    LIMIT 5;
                    """,
                    (perfume_id,),
                )
                occasion_rows = cur.fetchall()

        conn.close()

        notes_map = {"TOP": [], "MIDDLE": [], "BASE": []}
        for row in note_rows:
            note = (row.get("note") or "").strip()
            note_type = (row.get("type") or "").strip().upper()
            if not note or note_type not in notes_map:
                continue
            if note not in notes_map[note_type]:
                notes_map[note_type].append(note)

        notes = PerfumeNotes(
            top=notes_map["TOP"],
            middle=notes_map["MIDDLE"],
            base=notes_map["BASE"],
        )

        accords = [
            RatioItem(name=row["accord"], ratio=normalize_ratio(row.get("ratio")))
            for row in accord_rows
        ]
        seasons = [
            RatioItem(name=row["season"], ratio=normalize_ratio(row.get("ratio")))
            for row in season_rows
        ]
        occasions = [
            RatioItem(name=row["occasion"], ratio=normalize_ratio(row.get("ratio")))
            for row in occasion_rows
        ]

        return PerfumeDetailResponse(
            perfume_id=basic["perfume_id"],
            name=basic["perfume_name"],
            brand=basic["perfume_brand"],
            image_url=basic["img_link"],
            release_year=basic.get("release_year"),
            concentration=basic.get("concentration"),
            perfumer=basic.get("perfumer"),
            notes=notes,
            accords=accords,
            seasons=seasons,
            occasions=occasions,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching perfume detail: {e}")
        raise
