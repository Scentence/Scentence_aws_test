# 향수 검색 및 자동완성 고도화 계획 (Search & Autocomplete Enhancement)

## 1. 개요
현재의 단순 `ILIKE` 매칭 방식은 정확한 입력(띄어쓰기 포함)을 요구하여 사용자 경험이 떨어집니다. 사용자가 "chanel 5"라고 입력해도 "Chanel No.5"를 찾을 수 있도록 유연한 검색 로직을 구현합니다.

## 2. 주요 개선 사항

### A. 띄어쓰기 유연성 (Space-Insensitive Search)
- **DB 컬럼**: DB의 향수 이름/브랜드에서 공백을 제거한 값과 비교합니다.
- **입력값**: 사용자 입력에서도 공백을 제거합니다.
- **구현 방식**:
    ```sql
    WHERE REPLACE(b.perfume_name, ' ', '') ILIKE %s
    ```
    (입력값 `q`도 `q.replace(" ", "")` 처리 후 전달)

### B. 숫자/동의어 변환 (Synonym Handling)
- **숫자 변환**: 사용자가 "5"를 입력시 "Five"도 검색되고, "No.5"도 검색되도록 처리합니다.
- **구현 방식 (Python-side Preprocessing)**:
    - 입력어에 특정 패턴이 있으면, 변환된 검색어도 OR 조건으로 추가합니다.
    - 예: `q="5"` -> `queries=["%5%", "%five%", "%no.5%"]`
    - 예: `q="channel"` -> `queries=["%chanel%", "%channel%"]` (자주 틀리는 오타 보정)

### C. 검색 로직 개선 (Backend: [routers/perfumes.py](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence-app/backend/routers/perfumes.py))
현재의 단순 OR 검색을 개선하여, **'입력된 단어들이 모두 포함된 결과'**를 우선순위로 둡니다.

1. **검색어 정규화**:
   - `input`: "  Chanel   5  " -> `normalized`: "Chanel5" (공백 제거)
   - `tokens`: ["Chanel", "5"] (공백 기준 분리)

2. **SQL 쿼리 전략**:
   - **Level 1 (정확도 높음)**: 공백 제거 후 `ILIKE` 매칭 (가장 강력)
   - **Level 2 (토큰 매칭)**: "Chanel"과 "5"가 둘 다 포함된 레코드 검색
   
   ```python
   # Python Pseudocode
   search_term_clean = f"%{q.replace(' ', '')}%"
   
   # SQL
   WHERE REPLACE(b.perfume_name, ' ', '') ILIKE %(search_term_clean)s
      OR REPLACE(k.name_kr, ' ', '') ILIKE %(search_term_clean)s
   ```

## 3. 구현 단계 (Step-by-Step)

1. **[Step 1] Utils 함수 추가**: `backend/utils.py` (또는 내부 함수)
    - `normalize_search_term(q)`: 공백 제거, 소문자 변환
    - `generate_synonyms(q)`: "5"->"five", "V"->"5" 등 동의어 리스트 생성

2. **[Step 2] [search_perfumes](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence-app/backend/agent/database.py#175-269) 및 [autocomplete_perfumes](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence-app/backend/routers/perfumes.py#108-153) API 수정**
    - [users.py](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence-app/backend/routers/users.py) 나 [perfumes.py](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence-app/backend/routers/perfumes.py)의 쿼리에 `REPLACE(col, ' ', '')` 적용.
    - [get_perfume_db()](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence-app/backend/routers/perfumes.py#39-42) 연결 및 쿼리 실행 로직 업데이트.

3. **[Step 3] 테스트**
    - "chanel 5", "chanel five", "샤넬 넘버5" 등으로 검색하여 결과 확인.

## 4. 예상 효과
- "Jo Malone"을 "Jomalone"으로 검색해도 결과 노출.
- "No.5"를 "number 5"나 "5"로 검색해도 결과 노출.
- 훨씬 직관적이고 적은 타이핑으로 원하는 향수 발견 가능.
