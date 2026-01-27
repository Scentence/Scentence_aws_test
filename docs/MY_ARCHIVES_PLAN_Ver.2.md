# 🎯 관심 향수 (My Perfumes) 기능 구현 계획서 최종

> **목표:** 유저가 향수를 관심 목록에 추가/삭제/조회할 수 있는 기능 구현
>
> **작성일:** 2025-01-22
>
> **예상 파일 변경:** 6개 파일 (신규 2개, 수정 4개)

 📄 가이드 파일 위치                                                                                                            
                                                                                                                                 
  docs/MY_ARCHIVES_PLAN_Ver.2.md                                                                                                 
                                                                                                                                 
  오늘 순서                                                                                                                      
                                                                                                                                 
  Step 0: DB 테이블 생성 (AWS RDS)                                                                                               
      ↓                                                                                                                          
  Step 1: backend/routers/recom.py 복붙                                                                                          
      ↓                                                                                                                          
  Step 2: backend/routers/perfumes.py 복붙                                                                                       
      ↓                                                                                                                          
  Step 3: backend/main.py 수정                                                                                                   
      ↓                                                                                                                          
  Step 4: 프론트엔드 파일 2개 복붙                                                                                               
      ↓                                                                                                                          
  서버 재시작 → 테스트  
>
> **기능 설계**

위시, 보유 두가지만 뜨고

삭제시 

“이 향수 어땠나요?”
	•	👎 별로였다  → -1
	•	😐 무난했다  → 0
	•	👍 좋았다     → 1

✅ My Archives 설계 요약 (최종)

1. 테이블 목적

TB_MEMBER_MY_PERFUME_T -> My Archives(내 향수 옷장) 기능을 위한 원본 테이블
유저가 직접 등록한 향수, 시스템의 추천 향수를 저장.
등록된 향수의(보유/경험/관심)상태와 유저취향 반응을 저장.
추천 시스템 개인화 입력 데이터.

⸻

2. STATUS (HAVE / HAD / WANT) 도입 이유
	•	유저와 향수의 객관적 관계 상태를 표현
	•	My Archives UI에서 색 태그로 구분
	•	보유 / 과거 사용 / 관심 향수 분리 관리
	•	추천 맥락 강화 및 커머스 확장 기반

👉 STATUS는 “사실(관계)” 데이터

⸻

3. PREFERENCE (-1 / 0 / 1) 도입 이유
	•	유저의 주관적 취향 평가 저장
	•	추천 시스템의 명시적 학습 신호
	•	특히 ‘싫음(-1)’은 개인 필터 + 전체 품질 개선에 핵심
	•	1 : 좋음
	•	0 : 보통(중립/완충 구간)
	•	-1 : 싫음(강한 회피 신호)

👉 PREFERENCE는 “감정(취향)” 데이터

⸻

4. UI/UX 원칙
	•	HAVE/HAD/WANT는 색 태그로 표현
	•	👎 싫음은 My Archives 메인 옷장이 아니라
‘취향 관리/추천 제외’ 영역에서 관리
	•	챗봇 추천 향수 선택 시
페이지 이동 없이 모달/바텀시트로 액션 UI 제공

⸻

5. DB 구조 원칙
	•	STATUS는 컬럼으로 충분 (태그용 테이블 불필요)
	•	UNIQUE(member_id, perfume_id)로 중복 방지
	•	회원/향수/추천 결과 테이블과 역할 분리

⸻

>
> **UX 흐름 설계 아이디어**

🔹 유저가 향수 추천 받음

→ 👍 / 😐 / 👎

⸻

🔹 👍 / 😐 선택 시
	•	“내 향수 옷장에 추가할까요?”
	•	→ HAVE / HAD / WANT 선택
	•	→ My Archives에 표시

⸻

🔹 👎 선택 시
	•	“추천에 반영할게요”
	•	“이 계열은 피해서 추천할게요”

UI 결과:
	•	❌ 옷장에 안 보임
	•	✅ “기피 향수” 설정 영역에만 보임
---

## 🗓️ 작업 일정

### 오늘 할 것 (Step 0~4)
| 순서 | 작업 | 파일 |
|------|------|------|
| 0 | DB 테이블 생성 | AWS RDS (recom_db) |
| 1 | 관심향수 API | `backend/routers/recom.py` (신규) |
| 2 | 향수 검색 API | `backend/routers/perfumes.py` (신규) |
| 3 | 라우터 등록 | `backend/main.py` (수정) |
| 4 | 프론트엔드 | `archives/page.tsx`, `PerfumeSearchModal.tsx` |

### 내일 할 것 (Step 5)
- 챗봇 연동 (`perfume_id` 응답 추가)
- 선호도(PREFERENCE) UI
- 상태 변경 기능 (HAVE ↔ HAD ↔ WANT)

---

## 🔄 유저 등록 플로우

```
1. 유저가 Archives 페이지에서 "향수 추가" 버튼 클릭
                    ↓
2. 검색 모달 열림
                    ↓
3. "샤넬" 검색 → GET /perfumes/search?q=샤넬
                    ↓
4. tb_perfume_basic_m에서 ILIKE 검색
   (perfume_name OR perfume_brand에 "샤넬" 포함)
   → 4184개 향수 중 매칭되는 것 최대 20개 반환
                    ↓
5. 검색 결과 표시 (perfume_id, name, brand, image_url)
                    ↓
6. 유저가 원하는 향수 선택 → "추가" 버튼 클릭
                    ↓
7. POST /recom/my-perfumes
   (member_id, perfume_id, status="WANT", source="USER")
                    ↓
8. recom_db.TB_MEMBER_MY_PERFUME_T에 저장
                    ↓
9. Archives 목록 새로고침 → 등록된 향수 표시
```

---

## 📋 목차

1. [개요](#1-개요)
2. [Step 0: DB 테이블 생성](#step-0-db-테이블-생성)
3. [Step 1: 관심향수 API](#step-1-관심향수-api)
4. [Step 2: 향수 검색 API](#step-2-향수-검색-api)
5. [Step 3: main.py에 라우터 등록](#step-3-mainpy에-라우터-등록)
6. [Step 4: 프론트엔드](#step-4-프론트엔드)
7. [테스트 방법](#테스트-방법)
8. [내일 할 것: 챗봇 연동](#내일-할-것-챗봇-연동)

---

## 1. 개요

### 아키텍처

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   Backend       │────▶│   Database      │
│   (Next.js)     │     │   (FastAPI)     │     │   (PostgreSQL)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                       │
                              ┌────────────────────────┼────────────────────────┐
                              │                        │                        │
                        ┌─────▼─────┐          ┌──────▼──────┐          ┌──────▼──────┐
                        │ member_db │          │ perfume_db  │          │  recom_db   │
                        │ (회원정보) │          │ (향수정보)   │          │ (관심향수)   │
                        └───────────┘          └─────────────┘          └─────────────┘
```

### 사용할 DB 테이블 (recom_db)

```sql
-- 테이블: TB_MEMBER_MY_PERFUME_T
-- AWS RDS에 생성 필요

CREATE TABLE TB_MEMBER_MY_PERFUME_T (
    MEMBER_ID       BIGINT NOT NULL,                 -- FK (member_db)
    PERFUME_ID      BIGINT NOT NULL,                 -- FK (perfume_db)
    PERFUME_NAME    VARCHAR(200),                    -- 스냅샷 (선택)
    register_status VARCHAR(20) DEFAULT 'HAVE',      -- 'HAVE', 'HAD', 'RECOMMENDED'
    PREFERENCE      VARCHAR(20) DEFAULT 'NEUTRAL',   -- 'BAD', 'NEUTRAL', 'GOOD'
    register_reason VARCHAR(200),                    -- 등록 경로 'USER', 'RECOMMENDER'
    register_dt     TIMESTAMP DEFAULT NOW(),         -- 등록 일시
    alter_dt        TIMESTAMP DEFAULT NOW(),         -- 수정 일시

    UNIQUE (MEMBER_ID, PERFUME_ID)
);

-- 인덱스 (조회 성능)
CREATE INDEX idx_my_perfume_member ON TB_MEMBER_MY_PERFUME_T(MEMBER_ID);
```

**컬럼 설명:**
| 컬럼 | 설명 | 값 |
|------|------|-----|
| STATUS | 유저 관점 상태 | HAVE(보유중), HAD(과거), RECOMMENDED(추천) |
| register_reason | 등록 출처 | USER(직접등록), RECOMMENDER(챗봇추천) |
| PREFERENCE | 선호도 | -1(싫음), 0(보통), 1(좋음) |

### API 엔드포인트 설계

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/recom/my-perfumes?member_id=123` | 내 관심향수 목록 |
| POST | `/recom/my-perfumes` | 관심향수 추가 |
| DELETE | `/recom/my-perfumes/{perfume_id}?member_id=123` | 관심향수 삭제 |
| GET | `/perfumes/search?q=샤넬` | 향수 검색 |

---

## Step 0: DB 테이블 생성

### AWS RDS에서 실행 (recom_db)

DBeaver 또는 psql로 `recom_db`에 접속 후 아래 SQL 실행:

```sql
-- 테이블 생성
CREATE TABLE IF NOT EXISTS TB_MEMBER_MY_PERFUME_T (
    MY_PERFUME_ID   BIGSERIAL PRIMARY KEY,
    MEMBER_ID       BIGINT NOT NULL,
    PERFUME_ID      BIGINT NOT NULL,
    PERFUME_NAME    VARCHAR(200),
    STATUS          VARCHAR(20) DEFAULT 'WANT',
    SOURCE          VARCHAR(20) DEFAULT 'USER',
    PREFERENCE      SMALLINT DEFAULT 0,
    REGISTER_DT     TIMESTAMP DEFAULT NOW(),

    UNIQUE (MEMBER_ID, PERFUME_ID)
);

-- 인덱스 생성 (조회 성능)
CREATE INDEX IF NOT EXISTS idx_my_perfume_member
ON TB_MEMBER_MY_PERFUME_T(MEMBER_ID);

-- 확인
SELECT * FROM TB_MEMBER_MY_PERFUME_T LIMIT 5;
```

### DB 접속 정보 (참고용)

```
Host: db-server.c3sseu2wg3ho.ap-northeast-2.rds.amazonaws.com
Port: 5435
Database: recom_db
User: postgres
Password: teamscent123!
```

---

## Step 1: 관심향수 API

### 📁 파일: `backend/routers/recom.py` (신규 생성)

이 파일을 `backend/routers/` 폴더에 새로 만드세요.

```python
"""
관심 향수 (My Perfumes) API 라우터
- recom_db: 유저의 관심향수 데이터
- perfume_db: 향수 상세 정보
"""

import os
from datetime import datetime
from typing import List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/recom", tags=["My Perfumes"])

# ============================================================
# 환경변수 헬퍼
# ============================================================

def _get_env(key: str, default: str) -> str:
    return os.environ.get(key, default)

# ============================================================
# DB 연결 설정
# ============================================================

# recom_db 연결 (관심향수 저장)
RECOM_DB_PARAMS = {
    "dbname": "recom_db",
    "user": _get_env("DB_USER", "postgres"),
    "password": _get_env("DB_PASSWORD", "teamscent123!"),
    "host": _get_env("DB_HOST", "db-server.c3sseu2wg3ho.ap-northeast-2.rds.amazonaws.com"),
    "port": _get_env("DB_PORT", "5435"),
}

# perfume_db 연결 (향수 상세정보)
PERFUME_DB_PARAMS = {
    "dbname": "perfume_db",
    "user": _get_env("DB_USER", "postgres"),
    "password": _get_env("DB_PASSWORD", "teamscent123!"),
    "host": _get_env("DB_HOST", "db-server.c3sseu2wg3ho.ap-northeast-2.rds.amazonaws.com"),
    "port": _get_env("DB_PORT", "5435"),
}


def get_recom_db():
    """recom_db 연결"""
    return psycopg2.connect(**RECOM_DB_PARAMS, cursor_factory=RealDictCursor)


def get_perfume_db():
    """perfume_db 연결"""
    return psycopg2.connect(**PERFUME_DB_PARAMS, cursor_factory=RealDictCursor)


# ============================================================
# Pydantic 모델 (Request/Response)
# ============================================================

class MyPerfumeResponse(BaseModel):
    """관심향수 응답 모델"""
    my_perfume_id: int
    perfume_id: int
    name: str
    brand: str
    image_url: Optional[str]
    status: str       # HAVE, HAD, WANT
    source: str       # USER, RECOMMENDER
    preference: int   # -1, 0, 1
    registered_at: str


class AddPerfumeRequest(BaseModel):
    """관심향수 추가 요청 모델"""
    member_id: int
    perfume_id: int
    status: str = "HAVE"       # HAVE, HAD, WANT
    source: str = "USER"       # USER (직접등록), RECOMMENDER (챗봇추천)


class AddPerfumeResponse(BaseModel):
    """관심향수 추가 응답 모델"""
    success: bool
    message: str
    my_perfume_id: Optional[int] = None


# ============================================================
# API 엔드포인트
# ============================================================

@router.get("/my-perfumes", response_model=List[MyPerfumeResponse])
def get_my_perfumes(member_id: int = Query(..., description="회원 ID")):
    """
    내 관심향수 목록 조회

    - recom_db에서 유저의 향수 ID 목록 조회
    - perfume_db에서 향수 상세정보 조회
    - 두 데이터를 병합하여 반환
    """
    # 1. recom_db에서 유저의 관심향수 조회
    with get_recom_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    my_perfume_id,
                    perfume_id,
                    perfume_name,
                    status,
                    source,
                    preference,
                    register_dt
                FROM tb_member_my_perfume_t
                WHERE member_id = %s
                ORDER BY register_dt DESC
            """, (member_id,))
            my_perfumes = cur.fetchall()

    if not my_perfumes:
        return []

    # 2. perfume_db에서 향수 상세정보 조회
    perfume_ids = [p["perfume_id"] for p in my_perfumes]

    with get_perfume_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    perfume_id,
                    perfume_name,
                    perfume_brand,
                    img_link
                FROM tb_perfume_basic_m
                WHERE perfume_id = ANY(%s)
            """, (perfume_ids,))
            perfume_details = {p["perfume_id"]: p for p in cur.fetchall()}

    # 3. 데이터 병합
    result = []
    for mp in my_perfumes:
        detail = perfume_details.get(mp["perfume_id"], {})
        result.append(MyPerfumeResponse(
            my_perfume_id=mp["my_perfume_id"],
            perfume_id=mp["perfume_id"],
            name=detail.get("perfume_name", mp["perfume_name"]),
            brand=detail.get("perfume_brand", "Unknown"),
            image_url=detail.get("img_link"),
            status=mp["status"],
            source=mp["source"] or "USER",
            preference=mp["preference"] if mp["preference"] is not None else 0,
            registered_at=mp["register_dt"].isoformat() if mp["register_dt"] else "",
        ))

    return result


@router.post("/my-perfumes", response_model=AddPerfumeResponse)
def add_my_perfume(request: AddPerfumeRequest):
    """
    관심향수 추가

    - perfume_db에서 향수 존재 여부 확인
    - recom_db에 데이터 삽입 (중복 시 업데이트)
    """
    # 1. 향수 존재 여부 확인
    with get_perfume_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT perfume_id, perfume_name
                FROM tb_perfume_basic_m
                WHERE perfume_id = %s
            """, (request.perfume_id,))
            perfume = cur.fetchone()

    if not perfume:
        raise HTTPException(status_code=400, detail="존재하지 않는 향수입니다.")

    # 2. recom_db에 추가 (UPSERT)
    with get_recom_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tb_member_my_perfume_t
                    (member_id, perfume_id, perfume_name, status, source, preference, register_dt)
                VALUES (%s, %s, %s, %s, %s, 0, NOW())
                ON CONFLICT (member_id, perfume_id)
                DO UPDATE SET
                    status = EXCLUDED.status,
                    source = EXCLUDED.source,
                    register_dt = NOW()
                RETURNING my_perfume_id
            """, (request.member_id, request.perfume_id, perfume["perfume_name"],
                  request.status, request.source))
            result = cur.fetchone()
            conn.commit()

    return AddPerfumeResponse(
        success=True,
        message="관심향수에 추가되었습니다.",
        my_perfume_id=result["my_perfume_id"] if result else None
    )


@router.delete("/my-perfumes/{perfume_id}")
def delete_my_perfume(
    perfume_id: int,
    member_id: int = Query(..., description="회원 ID")
):
    """관심향수 삭제"""
    with get_recom_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM tb_member_my_perfume_t
                WHERE member_id = %s AND perfume_id = %s
            """, (member_id, perfume_id))
            deleted = cur.rowcount
            conn.commit()

    if deleted == 0:
        raise HTTPException(status_code=404, detail="해당 향수를 찾을 수 없습니다.")

    return {"success": True, "message": "삭제되었습니다."}
```

---

## Step 2: 향수 검색 API

### 📁 파일: `backend/routers/perfumes.py` (신규 생성)

향수 검색 API를 위한 별도 라우터입니다. (4184개 향수 중 검색)

```python
"""
향수 검색 API 라우터
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
    "user": _get_env("DB_USER", "postgres"),
    "password": _get_env("DB_PASSWORD", "teamscent123!"),
    "host": _get_env("DB_HOST", "db-server.c3sseu2wg3ho.ap-northeast-2.rds.amazonaws.com"),
    "port": _get_env("DB_PORT", "5435"),
}

def get_perfume_db():
    return psycopg2.connect(**PERFUME_DB_PARAMS, cursor_factory=RealDictCursor)


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

    with get_perfume_db() as conn:
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

    return [
        PerfumeSearchResult(
            perfume_id=r["perfume_id"],
            name=r["perfume_name"],
            brand=r["perfume_brand"],
            image_url=r["img_link"],
        )
        for r in results
    ]
```

---

## Step 3: main.py에 라우터 등록

### 📁 파일: `backend/main.py` (수정)

**찾을 위치:** 파일 상단의 import 부분

**추가할 코드:**

```python
# 기존 import 아래에 추가
from routers import recom, perfumes
```

**찾을 위치:** `app.include_router(users.router)` 부분

**추가할 코드:**

```python
# 기존 users.router 아래에 추가
app.include_router(recom.router)
app.include_router(perfumes.router)
```

---

## Step 4: 프론트엔드

### 📁 파일 4-1: `frontend/app/archives/page.tsx` (전체 교체)

기존 파일 내용을 아래로 **전체 교체**하세요.

```tsx
"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import Image from "next/image";
import Link from "next/link";
import ArchiveSidebar from "@/components/archives/ArchiveSidebar";
import PerfumeSearchModal from "@/components/archives/PerfumeSearchModal";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// 타입 정의
interface MyPerfume {
  my_perfume_id: number;
  perfume_id: number;
  name: string;
  brand: string;
  image_url: string | null;
  status: string;      // HAVE, HAD, WANT
  source: string;      // USER, RECOMMENDER
  preference: number;  // -1, 0, 1
  registered_at: string;
}

// 통계 아이템 컴포넌트
function StatItem({ label, count }: { label: string; count: number }) {
  return (
    <div className="text-center">
      <p className="text-2xl font-bold text-gray-800">{count}</p>
      <p className="text-sm text-gray-500">{label}</p>
    </div>
  );
}

// 향수 카드 컴포넌트
function PerfumeCard({
  perfume,
  onDelete,
}: {
  perfume: MyPerfume;
  onDelete: (id: number) => void;
}) {
  return (
    <div className="group relative flex flex-col gap-3 cursor-pointer transition-transform hover:-translate-y-1">
      {/* 삭제 버튼 */}
      <button
        onClick={() => onDelete(perfume.perfume_id)}
        className="absolute -top-2 -right-2 z-10 w-6 h-6 bg-red-500 text-white rounded-full
                   opacity-0 group-hover:opacity-100 transition-opacity text-xs font-bold"
      >
        ✕
      </button>

      {/* 이미지 */}
      <div className="aspect-[3/4] bg-gray-100 rounded-xl overflow-hidden">
        {perfume.image_url ? (
          <img
            src={perfume.image_url}
            alt={perfume.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            No Image
          </div>
        )}
      </div>

      {/* 정보 */}
      <div className="text-center">
        <p className="text-xs font-bold text-gray-800 truncate">{perfume.name}</p>
        <p className="text-[10px] text-gray-500 truncate">{perfume.brand}</p>
        <div className="flex justify-center gap-1 mt-1">
          {/* 상태 뱃지 */}
          <span
            className={`text-[10px] px-2 py-0.5 rounded-full ${
              perfume.status === "HAVE"
                ? "bg-blue-100 text-blue-600"
                : perfume.status === "WANT"
                ? "bg-yellow-100 text-yellow-600"
                : "bg-gray-100 text-gray-600"
            }`}
          >
            {perfume.status === "HAVE" ? "보유" : perfume.status === "WANT" ? "위시" : "과거"}
          </span>
          {/* 출처 뱃지 (챗봇 추천일 때만) */}
          {perfume.source === "RECOMMENDER" && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-pink-100 text-pink-600">
              추천
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ArchivesPage() {
  const { data: session } = useSession();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isSearchModalOpen, setIsSearchModalOpen] = useState(false);
  const [myPerfumes, setMyPerfumes] = useState<MyPerfume[]>([]);
  const [loading, setLoading] = useState(true);
  const [memberId, setMemberId] = useState<string | null>(null);

  // 회원 ID 가져오기 (NextAuth 또는 localStorage)
  useEffect(() => {
    if (session?.user?.id) {
      setMemberId(String(session.user.id));
    } else {
      const stored = localStorage.getItem("localAuth");
      if (stored) {
        const parsed = JSON.parse(stored);
        setMemberId(String(parsed.memberId));
      }
    }
  }, [session]);

  // 관심향수 목록 조회
  const fetchMyPerfumes = async () => {
    if (!memberId) return;

    try {
      setLoading(true);
      const res = await fetch(`${API_URL}/recom/my-perfumes?member_id=${memberId}`);
      if (res.ok) {
        const data = await res.json();
        setMyPerfumes(data);
      }
    } catch (error) {
      console.error("Failed to fetch my perfumes:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMyPerfumes();
  }, [memberId]);

  // 향수 삭제
  const handleDelete = async (perfumeId: number) => {
    if (!memberId) return;
    if (!confirm("정말 삭제하시겠습니까?")) return;

    try {
      const res = await fetch(
        `${API_URL}/recom/my-perfumes/${perfumeId}?member_id=${memberId}`,
        { method: "DELETE" }
      );
      if (res.ok) {
        setMyPerfumes((prev) => prev.filter((p) => p.perfume_id !== perfumeId));
      }
    } catch (error) {
      console.error("Failed to delete perfume:", error);
    }
  };

  // 향수 추가 완료 콜백
  const handleAddComplete = () => {
    setIsSearchModalOpen(false);
    fetchMyPerfumes(); // 목록 새로고침
  };

  // 통계 계산
  const stats = {
    have: myPerfumes.filter((p) => p.status === "HAVE").length,
    want: myPerfumes.filter((p) => p.status === "WANT").length,
    had: myPerfumes.filter((p) => p.status === "HAD").length,
    recommended: myPerfumes.filter((p) => p.source === "RECOMMENDER").length,
  };

  return (
    <div className="min-h-screen bg-[#FDFBF8]">
      {/* 헤더 */}
      <header className="fixed top-0 left-0 right-0 z-40 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-7xl mx-auto flex items-center justify-between px-6 py-4">
          <Link href="/">
            <Image src="/Scentence.png" alt="Logo" width={120} height={32} />
          </Link>
          <button
            onClick={() => setIsSidebarOpen(true)}
            className="p-2 hover:bg-gray-100 rounded-lg transition"
          >
            <Image src="/menu.png" alt="Menu" width={24} height={24} />
          </button>
        </div>
      </header>

      {/* 메인 컨텐츠 */}
      <main className="pt-[72px] pb-24 px-6">
        {/* 통계 바 */}
        <section className="w-full max-w-5xl mx-auto mb-10 mt-8">
          <div className="flex justify-between items-center bg-white rounded-2xl shadow-sm px-10 py-6">
            <StatItem label="보유" count={stats.have} />
            <StatItem label="위시" count={stats.want} />
            <StatItem label="과거" count={stats.had} />
            <StatItem label="추천받음" count={stats.recommended} />
          </div>
        </section>

        {/* 향수 추가 버튼 */}
        <section className="w-full max-w-5xl mx-auto mb-6">
          <button
            onClick={() => setIsSearchModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-pink-500 text-white rounded-lg
                       hover:bg-pink-600 transition font-medium"
          >
            <span className="text-lg">+</span>
            향수 추가
          </button>
        </section>

        {/* 향수 목록 */}
        <section className="w-full max-w-5xl mx-auto">
          {loading ? (
            <div className="text-center py-20 text-gray-500">불러오는 중...</div>
          ) : myPerfumes.length === 0 ? (
            <div className="text-center py-20 text-gray-500">
              <p className="text-lg mb-2">아직 등록된 향수가 없습니다</p>
              <p className="text-sm">위의 &apos;향수 추가&apos; 버튼을 눌러 시작하세요!</p>
            </div>
          ) : (
            <div className="grid grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-x-6 gap-y-12">
              {myPerfumes.map((perfume) => (
                <PerfumeCard
                  key={perfume.perfume_id}
                  perfume={perfume}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          )}
        </section>

        {/* 향수 관계 맵 버튼 */}
        <Link
          href="/perfume-network"
          className="fixed bottom-8 right-8 px-5 py-3 bg-gradient-to-r from-rose-400 to-pink-400
                     text-white rounded-full shadow-lg hover:shadow-xl transition font-medium"
        >
          향수 관계 맵
        </Link>
      </main>

      {/* 사이드바 */}
      <ArchiveSidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

      {/* 검색 모달 */}
      {isSearchModalOpen && (
        <PerfumeSearchModal
          memberId={memberId}
          onClose={() => setIsSearchModalOpen(false)}
          onAddComplete={handleAddComplete}
        />
      )}
    </div>
  );
}
```

---

### 📁 파일 4-2: `frontend/components/archives/PerfumeSearchModal.tsx` (신규 생성)

`frontend/components/archives/` 폴더에 새로 만드세요.

```tsx
"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SearchResult {
  perfume_id: number;
  name: string;
  brand: string;
  image_url: string | null;
}

interface Props {
  memberId: string | null;
  onClose: () => void;
  onAddComplete: () => void;
}

export default function PerfumeSearchModal({ memberId, onClose, onAddComplete }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [adding, setAdding] = useState<number | null>(null);

  // 검색 실행
  const handleSearch = async () => {
    if (!query.trim()) return;

    try {
      setLoading(true);
      const res = await fetch(`${API_URL}/perfumes/search?q=${encodeURIComponent(query)}`);
      if (res.ok) {
        const data = await res.json();
        setResults(data);
      }
    } catch (error) {
      console.error("Search failed:", error);
    } finally {
      setLoading(false);
    }
  };

  // Enter 키 처리
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  // 향수 추가
  const handleAdd = async (perfume: SearchResult) => {
    if (!memberId) {
      alert("로그인이 필요합니다.");
      return;
    }

    try {
      setAdding(perfume.perfume_id);
      const res = await fetch(`${API_URL}/recom/my-perfumes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          member_id: parseInt(memberId),
          perfume_id: perfume.perfume_id,
          status: "HAVE",
          source: "USER",
        }),
      });

      if (res.ok) {
        alert(`"${perfume.name}" 이(가) 추가되었습니다!`);
        onAddComplete();
      } else {
        const error = await res.json();
        alert(error.detail || "추가에 실패했습니다.");
      }
    } catch (error) {
      console.error("Add failed:", error);
      alert("추가에 실패했습니다.");
    } finally {
      setAdding(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-2xl w-full max-w-lg mx-4 max-h-[80vh] flex flex-col">
        {/* 헤더 */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-bold">향수 검색</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition"
          >
            ✕
          </button>
        </div>

        {/* 검색 입력 */}
        <div className="p-4 border-b">
          <div className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="향수 이름 또는 브랜드 검색..."
              className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-pink-300"
            />
            <button
              onClick={handleSearch}
              disabled={loading}
              className="px-4 py-2 bg-pink-500 text-white rounded-lg hover:bg-pink-600
                         transition disabled:opacity-50"
            >
              {loading ? "..." : "검색"}
            </button>
          </div>
        </div>

        {/* 검색 결과 */}
        <div className="flex-1 overflow-y-auto p-4">
          {results.length === 0 ? (
            <div className="text-center py-10 text-gray-500">
              검색어를 입력하세요
            </div>
          ) : (
            <div className="space-y-3">
              {results.map((perfume) => (
                <div
                  key={perfume.perfume_id}
                  className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition"
                >
                  {/* 이미지 */}
                  <div className="w-16 h-20 bg-gray-200 rounded-lg overflow-hidden flex-shrink-0">
                    {perfume.image_url ? (
                      <img
                        src={perfume.image_url}
                        alt={perfume.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-gray-400 text-xs">
                        No Image
                      </div>
                    )}
                  </div>

                  {/* 정보 */}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-800 truncate">{perfume.name}</p>
                    <p className="text-sm text-gray-500 truncate">{perfume.brand}</p>
                  </div>

                  {/* 추가 버튼 */}
                  <button
                    onClick={() => handleAdd(perfume)}
                    disabled={adding === perfume.perfume_id}
                    className="px-3 py-1.5 bg-pink-500 text-white text-sm rounded-lg
                               hover:bg-pink-600 transition disabled:opacity-50 flex-shrink-0"
                  >
                    {adding === perfume.perfume_id ? "..." : "추가"}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

---

## 내일 할 것: 챗봇 연동

> ⚠️ **이 단계는 내일 진행합니다.** 오늘은 Step 0~4만 완료하세요.

### 5-1. 스키마에 perfume_id 추가

### 📁 파일: `backend/agent/schemas.py` (수정)

**찾을 위치:** `class PerfumeDetail(BaseModel):` 부분

**수정 전:**
```python
class PerfumeDetail(BaseModel):
    perfume_name: str
    perfume_brand: str
    # ... 나머지
```

**수정 후:**
```python
class PerfumeDetail(BaseModel):
    perfume_id: int  # 이 줄 추가
    perfume_name: str
    perfume_brand: str
    # ... 나머지
```

### 5-2. 챗봇 응답에서 버튼 렌더링

### 📁 파일: `frontend/components/Chat/MessageItem.tsx` (수정)

**찾을 위치:** `const components` 부분 (react-markdown의 커스텀 렌더러)

`p` 태그 렌더러에 `[REGISTER:id]` 패턴 감지 로직 추가:

```tsx
// [REGISTER:123] 패턴을 버튼으로 변환하는 함수
function parseRegisterTags(text: string, onRegister: (id: number) => void) {
  const regex = /\[REGISTER:(\d+)\]/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    // 매치 전 텍스트
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    // 버튼으로 변환
    const perfumeId = parseInt(match[1]);
    parts.push(
      <button
        key={match.index}
        onClick={() => onRegister(perfumeId)}
        className="inline-flex items-center gap-1 px-2 py-1 bg-pink-500 text-white
                   text-xs rounded-full hover:bg-pink-600 transition mx-1"
      >
        + 저장
      </button>
    );
    lastIndex = regex.lastIndex;
  }

  // 남은 텍스트
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? parts : text;
}
```

---

## 테스트 방법

### 1. 백엔드 테스트 (터미널)

```bash
# 백엔드 서버 실행 후

# 1. 향수 검색 테스트
curl "http://localhost:8000/perfumes/search?q=chanel"

# 2. 관심향수 추가 테스트 (직접 등록)
curl -X POST "http://localhost:8000/recom/my-perfumes" \
  -H "Content-Type: application/json" \
  -d '{"member_id": 1, "perfume_id": 123, "status": "HAVE", "source": "USER"}'

# 3. 관심향수 추가 테스트 (챗봇 추천 저장)
curl -X POST "http://localhost:8000/recom/my-perfumes" \
  -H "Content-Type: application/json" \
  -d '{"member_id": 1, "perfume_id": 456, "status": "WANT", "source": "RECOMMENDER"}'

# 4. 관심향수 목록 조회
curl "http://localhost:8000/recom/my-perfumes?member_id=1"

# 5. 관심향수 삭제
curl -X DELETE "http://localhost:8000/recom/my-perfumes/123?member_id=1"
```

### 2. 프론트엔드 테스트

1. `http://localhost:3000/archives` 접속
2. "향수 추가" 버튼 클릭
3. 향수 이름 검색 (예: "샤넬")
4. 결과에서 "추가" 버튼 클릭
5. 목록에 향수가 나타나는지 확인
6. 향수 카드 위에 마우스 올려서 삭제 버튼 확인

---

## 오늘 체크리스트

- [ ] **Step 0:** `recom_db`에 테이블 생성 (AWS RDS)
- [ ] **Step 1:** `backend/routers/recom.py` 생성
- [ ] **Step 2:** `backend/routers/perfumes.py` 생성
- [ ] **Step 3:** `backend/main.py`에 라우터 등록
- [ ] **Step 4-1:** `frontend/app/archives/page.tsx` 교체
- [ ] **Step 4-2:** `frontend/components/archives/PerfumeSearchModal.tsx` 생성
- [ ] 백엔드 서버 재시작
- [ ] 프론트엔드 서버 재시작
- [ ] API 테스트 (curl)
- [ ] UI 테스트 (브라우저)

---

## 문제 해결

### DB 연결 오류
- 환경변수 확인: `DB_HOST`, `DB_USER`, `DB_PASSWORD`
- Docker 환경이면 `host.docker.internal` 사용

### CORS 오류
- `backend/main.py`의 `allow_origins`에 프론트엔드 주소 포함 확인

### 404 오류
- `main.py`에서 라우터가 제대로 등록되었는지 확인
- 서버 재시작 필요
