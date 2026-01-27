# My Archives 기능 구현 계획서 Ver.3

## 목표
향수 검색 모달에서 한글/영어로 향수를 검색하고, 등록된 향수를 My Archives에서 관리할 수 있는 기능 완성

## 현재 상태 분석

### 이미 완성된 부분
| 항목 | 상태 | 위치 |
|------|------|------|
| Frontend UI | ✅ 완성 | `frontend/app/archives/page.tsx` |
| PerfumeSearchModal | ✅ 완성 | `frontend/components/archives/PerfumeSearchModal.tsx` |
| PerfumeDetailModal | ✅ 완성 | `frontend/components/archives/PerfumeDetailModal.tsx` |
| 향수 검색 API 코드 | ✅ 존재 | `backend/routers/perfumes.py` |
| 향수 저장 API | ✅ 존재 | `backend/routers/users.py` (`/users/me/perfumes`) |
| TB_MEMBER_MY_PERFUME_T | ✅ 존재 | recom_db |
| TB_PERFUME_NAME_KR | ✅ 존재 | perfume_db (한글 데이터) |

### 미완성 부분 (수정 필요)
| 항목 | 문제점 | 우선순위 |
|------|--------|---------|
| perfumes 라우터 미등록 | main.py에 등록 안됨 → API 작동 안함 | 🔴 Critical |
| 한글 검색 미지원 | perfumes.py가 영어만 검색 | 🔴 Critical |
| 향수 목록 조회 API 없음 | 페이지 로드 시 저장된 향수 못 불러옴 | 🟡 High |
| 상태 변경 API 없음 | HAVE ↔ WANT 변경 저장 불가 | 🟡 High |
| 향수 삭제 API 없음 | 삭제 기능 Backend 없음 | 🟡 High |

---

## 작업 순서

### Step 1: Backend - main.py에 라우터 등록
**파일:** `backend/main.py`

```python
# 추가할 import
from routers import perfumes

# 추가할 라우터 등록
app.include_router(perfumes.router)
```

---

### Step 2: Backend - perfumes.py 한글 검색 기능 추가
**파일:** `backend/routers/perfumes.py`

**수정 내용:**
- `TB_PERFUME_NAME_KR` 테이블과 LEFT JOIN
- `name_kr`, `brand_kr`, `search_keywords` 컬럼도 검색 대상에 추가

**수정된 쿼리:**
```sql
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
    OR k.search_keywords ILIKE %s
LIMIT 20
```

**응답 모델 수정:**
```python
class PerfumeSearchResult(BaseModel):
    perfume_id: int
    name: str           # 영문명
    name_kr: Optional[str]  # 한글명 (추가)
    brand: str          # 영문 브랜드
    brand_kr: Optional[str] # 한글 브랜드 (추가)
    image_url: Optional[str]
```

---

### Step 3: Backend - users.py에 향수 관리 API 추가
**파일:** `backend/routers/users.py`

**추가할 엔드포인트:**

#### 3-1. 내 향수 목록 조회
```
GET /users/{member_id}/perfumes
```
- recom_db.TB_MEMBER_MY_PERFUME_T에서 조회
- perfume_db.TB_PERFUME_BASIC_M과 JOIN하여 상세 정보 반환

#### 3-2. 향수 상태 변경
```
PATCH /users/{member_id}/perfumes/{perfume_id}
Body: { "register_status": "HAVE" | "HAD" | "RECOMMENDED", "preference": "BAD" | "NEUTRAL" | "GOOD" }
```

#### 3-3. 향수 삭제
```
DELETE /users/{member_id}/perfumes/{perfume_id}
```

---

### Step 4: Frontend - API 연동 완성
**파일:** `frontend/app/archives/page.tsx`

**수정 내용:**
1. useEffect에서 `GET /users/{memberId}/perfumes` 호출하여 초기 데이터 로드
2. 상태 변경 시 `PATCH` API 호출
3. 삭제 시 `DELETE` API 호출

**파일:** `frontend/components/archives/PerfumeSearchModal.tsx`

**수정 내용:**
1. 검색 결과에 한글명(name_kr) 표시
2. "추가" 버튼 대신 "보유(HAVE)", "과거(HAD)" 두 버튼 표시
3. 향수 추가 시 선택한 상태(register_status)와 함께 API 호출

---

## 데이터 흐름

### Archives에서 직접 등록
```
[유저가 "샤넬" 검색]
        ↓
GET /perfumes/search?q=샤넬
        ↓
Backend: TB_PERFUME_BASIC_M + TB_PERFUME_NAME_KR JOIN
        ↓
name_kr ILIKE '%샤넬%' OR brand_kr ILIKE '%샤넬%'
        ↓
[검색 결과 반환 (영문명 + 한글명)]
        ↓
[유저가 "보유(HAVE)" 또는 "과거(HAD)" 버튼 클릭]
        ↓
POST /users/me/perfumes
Body: {
    member_id,
    perfume_id,
    perfume_name,
    register_status: "HAVE" | "HAD",  ← 유저가 선택
    register_reason: "USER"
}
        ↓
Backend: TB_MEMBER_MY_PERFUME_T에 INSERT
        ↓
[Archives 페이지에서 조회]
        ↓
GET /users/{member_id}/perfumes
        ↓
[저장된 향수 목록 표시]
```

### 챗봇에서 추천받아 등록 (추후 구현)
```
[챗봇이 향수 추천]
        ↓
[유저가 "저장" 버튼 클릭]
        ↓
POST /users/me/perfumes
Body: {
    member_id,
    perfume_id,
    perfume_name,
    register_status: "RECOMMENDED",  ← 자동 설정
    register_reason: "RECOMMENDER"
}
        ↓
[Archives에 추천받은 향수로 표시]
```

---

## DB 테이블 참조

### TB_PERFUME_BASIC_M (perfume_db) - 4184개 향수
| 컬럼 | 설명 |
|------|------|
| perfume_id | PK |
| perfume_name | 영문 향수명 |
| perfume_brand | 영문 브랜드 |
| img_link | 이미지 URL |

### TB_PERFUME_NAME_KR (perfume_db) - 한글 매핑
| 컬럼 | 설명 |
|------|------|
| perfume_id | FK |
| name_kr | 한글 향수명 |
| brand_kr | 한글 브랜드명 |
| search_keywords | 검색 키워드 |

### TB_MEMBER_MY_PERFUME_T (recom_db) - 유저 향수 저장
| 컬럼 | 설명 | 값 |
|------|------|-----|
| MEMBER_ID | 회원 ID | FK |
| PERFUME_ID | 향수 ID | FK |
| PERFUME_NAME | 향수명 스냅샷 | |
| register_status | 보유 상태 | HAVE(보유중), HAD(과거), RECOMMENDED(추천받음) |
| PREFERENCE | 선호도 | BAD, NEUTRAL, GOOD |
| register_reason | 등록 출처 | USER, RECOMMENDER |
| register_dt | 등록일시 | |
| alter_dt | 수정일시 | |

---

## 수정할 파일 목록

| 순서 | 파일 | 작업 |
|------|------|------|
| 1 | `backend/main.py` | perfumes 라우터 등록 |
| 2 | `backend/routers/perfumes.py` | 한글 검색 기능 추가 |
| 3 | `backend/routers/users.py` | 향수 조회/변경/삭제 API 추가 |
| 4 | `frontend/app/archives/page.tsx` | API 연동 (useEffect) |
| 5 | `frontend/components/archives/PerfumeSearchModal.tsx` | 한글명 표시 |

---

## 테스트 방법

### Backend API 테스트
```bash
# 1. 한글 검색 테스트
curl "http://localhost:8000/perfumes/search?q=샤넬"

# 2. 영어 검색 테스트
curl "http://localhost:8000/perfumes/search?q=chanel"

# 3. 향수 저장 테스트
curl -X POST "http://localhost:8000/users/me/perfumes" \
  -H "Content-Type: application/json" \
  -d '{"member_id": 1, "perfume_id": 123, "perfume_name": "Chanel No.5"}'

# 4. 내 향수 목록 조회
curl "http://localhost:8000/users/1/perfumes"

# 5. 상태 변경
curl -X PATCH "http://localhost:8000/users/1/perfumes/123" \
  -H "Content-Type: application/json" \
  -d '{"register_status": "WANT"}'

# 6. 삭제
curl -X DELETE "http://localhost:8000/users/1/perfumes/123"
```

### Frontend 테스트
1. `http://localhost:3000/archives` 접속
2. "향수 추가" 버튼 클릭
3. "샤넬" 또는 "Chanel" 검색
4. 검색 결과에 한글명이 표시되는지 확인
5. "보유" 또는 "위시" 버튼으로 추가
6. 페이지 새로고침 후에도 저장된 향수가 보이는지 확인

---

## 참고: 기존 플랜과의 차이점

| Ver.2 | Ver.3 |
|-------|-------|
| recom.py 신규 생성 | users.py에 기능 추가 (기존 구조 활용) |
| DB 테이블 생성 필요 | DB 테이블 이미 존재 |
| 한글 검색 언급 없음 | TB_PERFUME_NAME_KR JOIN으로 한글 검색 |
| 챗봇 연동 포함 | 챗봇 연동은 별도 작업으로 분리 |
