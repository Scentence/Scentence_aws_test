
### backend/main.py 수정

```python
# [1] 상단 import 부분에 perfumes 추가
from routers import users, perfumes  # <--- perfumes 추가 (15번줄)

# [2] app 생성 후 include_router 추가 (users 등록된 곳 아래에)
app.include_router(users.router)
app.include_router(perfumes.router)  # <--- 추가 (25번줄)
```

### backend/routers/perfumes.py 수정

```python
"""
향수 검색 API 라우터 (Re-created, 한글 검색 지원 Ver)
"""

"""
향수 검색 API 라우터 (한글 검색 지원 Ver)
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
    "host": _get_env("DB_HOST", "host.docker.internal"),
    "port": _get_env("DB_PORT", "5432"),
}

def get_perfume_db():
    conn = psycopg2.connect(**PERFUME_DB_PARAMS, cursor_factory=RealDictCursor)
    return conn

# ============================================================
# 모델
# ============================================================

class PerfumeSearchResult(BaseModel):
    perfume_id: int
    name: str
    name_kr: Optional[str] = None
    brand: str
    brand_kr: Optional[str] = None
    image_url: Optional[str] = None

# ============================================================
# API
# ============================================================

@router.get("/search", response_model=List[PerfumeSearchResult])
def search_perfumes(q: str = Query(..., min_length=1, description="검색어")):
    search_term = f"%{q}%"

    try:
        conn = get_perfume_db()
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT
                        b.perfume_id,
                        b.perfume_name,
                        b.perfume_brand,
                        b.img_link,
                        k.name_kr,
                        k.brand_kr
                    FROM tb_perfume_basic_m b
                    LEFT JOIN tb_perfume_name_kr k ON b.perfume_id = k.perfume_id
                    WHERE
                        b.perfume_name ILIKE %s
                        OR b.perfume_brand ILIKE %s
                        OR k.name_kr ILIKE %s
                        OR k.brand_kr ILIKE %s
                    LIMIT 20
                """, (search_term, search_term, search_term, search_term))
                results = cur.fetchall()
        
        conn.close()

        return [
            PerfumeSearchResult(
                perfume_id=r["perfume_id"],
                name=r["perfume_name"],
                name_kr=r["name_kr"],
                brand=r["perfume_brand"],
                brand_kr=r["brand_kr"],
                image_url=r["img_link"],
            )
            for r in results
        ]

    except Exception as e:
        print(f"Error searching perfumes: {e}")
        return []
```

### backend/routers/users.py 수정

```python
from agent.database import get_recom_db_connection, get_db_connection, release_recom_db_connection, release_db_connection, add_my_perfume # 추가 26.01.26 ksu

# 하단에 추가 26.01.26 ksu
# ============================================================
# [NEW] My Perfume Archives API
# ============================================================

class MyPerfumeRequest(BaseModel):
    perfume_id: int
    perfume_name: str
    register_status: str  # HAVE, HAD, RECOMMENDED
    register_reason: Optional[str] = "USER"
    preference: Optional[str] = "NEUTRAL"

class UpdatePerfumeStatusRequest(BaseModel):
    register_status: str
    preference: Optional[str] = None


@router.get("/{member_id}/perfumes")
def get_my_perfumes(member_id: int):
    """내 향수 목록 조회 (Basic Info + My Status)"""
    conn = get_recom_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # recom_db의 내 향수 테이블 조회
        # (이미지 등 상세 정보가 필요하다면 추후 perfume_db와 조인이 필요하지만, 
        #  현재 구조상 간단히 저장된 스냅샷 이름이나 ID를 반환하고
        #  Frontend에서 이미지를 위해 별도 호출하거나, 여기서 perfume_db를 추가 연결해야 합니다.
        #  일단 Frontend의 collection 구조에 맞춰 데이터 반환)
        cur.execute("""
            SELECT 
                p.member_id, p.perfume_id, p.perfume_name, p.register_status, p.preference,
                -- perfume_basic 정보는 별도로 가져오거나 여기서 생략 가능하나,
                -- 편의상 저장된 이름과 ID, 상태를 리턴합니다.
                p.register_dt
            FROM tb_member_my_perfume_t p
            WHERE p.member_id = %s
            ORDER BY p.register_dt DESC
        """, (member_id,))
        rows = cur.fetchall()
        return rows
    except Exception as e:
        print(f"Error getting my perfumes: {e}")
        return []
    finally:
        cur.close()
        conn.close()


@router.post("/{member_id}/perfumes")
def add_my_perfume_api(member_id: int, req: MyPerfumeRequest):
    """향수 등록 (HAVE / HAD 등)"""
    conn = get_recom_db_connection()
    cur = conn.cursor()
    try:
        # Upsert Logic
        cur.execute("""
            INSERT INTO tb_member_my_perfume_t 
            (member_id, perfume_id, perfume_name, register_status, preference, register_reason, register_dt)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (member_id, perfume_id) 
            DO UPDATE SET 
                register_status = EXCLUDED.register_status,
                preference = EXCLUDED.preference,
                alter_dt = NOW()
        """, (member_id, req.perfume_id, req.perfume_name, req.register_status, req.preference, req.register_reason))
        conn.commit()
        return {"status": "ok"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.patch("/{member_id}/perfumes/{perfume_id}")
def update_my_perfume(member_id: int, perfume_id: int, req: UpdatePerfumeStatusRequest):
    """향수 상태 변경 (HAVE <-> WANT 등)"""
    conn = get_recom_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE tb_member_my_perfume_t
            SET register_status = %s, preference = COALESCE(%s, preference), alter_dt = NOW()
            WHERE member_id = %s AND perfume_id = %s
        """, (req.register_status, req.preference, member_id, perfume_id))
        conn.commit()
        return {"status": "ok"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.delete("/{member_id}/perfumes/{perfume_id}")
def delete_my_perfume(member_id: int, perfume_id: int):
    """향수 삭제"""
    conn = get_recom_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            DELETE FROM tb_member_my_perfume_t
            WHERE member_id = %s AND perfume_id = %s
        """, (member_id, perfume_id))
        conn.commit()
        return {"status": "ok"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()
```

### frontend/app/archives/page.tsx 수정

