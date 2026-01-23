"""
향수 검색 API 라우터 (Re-created)
"""

import os
from typing import List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, Query
from pydantic import BaseModel

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
        conn = psycopg2.connect(**PERFUME_DB_PARAMS, cursor_factory=RealDictCursor)
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
    image_url: Optional[str]


# ============================================================
# API
# ============================================================

@router.get("/search", response_model=List[PerfumeSearchResult])
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
