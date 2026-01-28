# CK One 상큼 레이어링 요청 처리 흐름

요청 문장 예시: "ck one을 가지고 있는데 더 상큼하게 변하도록 레이어링 할 수 있는 향수 추천해줘."

이 문서에서는 위 요청이 들어왔을 때 어디서 무엇을 불러오고, 어떻게 저장하며, 화면에 어떻게 출력되는지 전체 흐름을 정리한다.

## 1) 사용자 입력과 프론트엔드 진입점

- 사용자 입력 위치: `C:\SKN_19\Scentence\Scentence\frontend\app\layering\page.tsx`
- 사용자는 채팅 입력창에 자연어로 질문을 입력한다.
- `handleAnalyze()`가 실행되며 다음을 수행한다.
  - 입력값 검증 및 채팅에 사용자 메시지 추가
  - 로딩 상태 및 에러 상태 초기화
  - 로컬 스토리지에서 `member_id`를 읽음 (`getMemberId()`)
  - API 호출: `POST ${apiBase}/analyze`

### API 엔드포인트 구성

- `apiBase`는 `NEXT_PUBLIC_LAYERING_API_URL`을 기반으로 만들며 기본값은 `/api/layering`이다.
- 최종 요청 경로: `/layering/analyze`

요청 바디 예시:

```json
{
  "user_text": "ck one을 가지고 있는데 더 상큼하게 변하도록 레이어링 할 수 있는 향수 추천해줘.",
  "member_id": 123,
  "save_recommendations": true,
  "save_my_perfume": false
}
```

## 2) 백엔드 API 진입점

- 서버 진입점: `C:\SKN_19\Scentence\Scentence\layering\main.py`
- 라우트: `POST /layering/analyze`
- 처리 함수: `layering_analyze()`

요청이 들어오면 다음 순서로 처리된다.

1. 레포지토리 로딩
   - `get_repository()`가 `PerfumeRepository()`를 생성하여 향수 벡터 데이터를 메모리에 적재한다.
   - 파일 위치: `C:\SKN_19\Scentence\Scentence\layering\agent\database.py`

2. 자연어 선호 추출
   - `analyze_user_input(user_text)` 호출
   - 파일 위치: `C:\SKN_19\Scentence\Scentence\layering\agent\graph.py`
   - 동작:
     - `OPENAI_API_KEY`가 있으면 LLM으로 키워드/강도 추출
     - 없으면 휴리스틱으로 `KEYWORD_MAP` 기반 키워드 탐지
- 키워드 매핑 정의: `C:\SKN_19\Scentence\Scentence\layering\agent\constants.py`
- 예시 텍스트의 "상큼"은 휴리스틱에 직접 매핑되어 있지 않으므로,
  - LLM이 `citrus`/`fresh` 같은 키워드를 추출하면 타깃 벡터에 반영됨
- "차가운", "플로럴" 같은 한국어 키워드는 `KEYWORD_MAP`에 직접 매핑되어
  - 휴리스틱에서도 키워드가 누락되지 않도록 보완됨

3. 질문에서 향수명 감지
   - `analyze_user_query(user_text, repository, preferences)` 호출
   - 파일 위치: `C:\SKN_19\Scentence\Scentence\layering\agent\graph.py`
   - 내부 동작:
     - 텍스트를 분리해 후보 검색 (`_split_query_segments`)
     - 향수 DB 이름 인덱스를 사용해 fuzzy 매칭 (`repository.find_perfume_candidates`)
     - 문장에 "가지고" 등이 포함된 경우 첫 향수를 베이스로 간주
   - 결과: CK One이 `base_perfume_id`로 선택됨

4. 추천 계산
   - 감지된 베이스 향수 ID로 `rank_recommendations()` 호출
   - 파일 위치: `C:\SKN_19\Scentence\Scentence\layering\agent\tools.py`
   - 로직 요약:
     - 사용자 키워드를 기반으로 타깃 벡터 생성 (`get_target_vector`)
     - 모든 후보 향수와 조합하여 점수 계산 (`calculate_advanced_layering`)
     - 적합한 후보만 필터링하고 상위 3개를 선택

## 3) 데이터 로딩 (DB에서 무엇을 불러오는가)

향수 데이터는 초기화 시 DB에서 읽어 메모리에 캐시된다.

- 데이터 로딩 위치: `C:\SKN_19\Scentence\Scentence\layering\agent\database.py`
- 사용 테이블:
  - `TB_PERFUME_BASIC_M`: 향수 기본 정보
  - `TB_PERFUME_ACCORD_R`: 어코드 비율
  - `TB_PERFUME_NOTES_M`: 베이스 노트

로드된 데이터는 `PerfumeVector`로 변환되며,
`PerfumeRepository` 안에 캐시되어 추천 계산에 사용된다.

## 4) 저장 동작 (어디에 어떻게 저장되는가)

`layering_analyze()`는 `member_id`와 저장 옵션에 따라 결과를 저장한다.

- 저장 위치: `C:\SKN_19\Scentence\Scentence\layering\agent\database.py`
- 저장 조건:
  - `member_id`가 존재하고 `save_recommendations`가 true일 때 추천 결과 저장
  - `save_my_perfume`가 true면 베이스 향수도 보유 목록에 저장

### 추천 결과 저장

- 함수: `save_recommendation_results()`
- 테이블: `TB_MEMBER_RECOM_RESULT_T`
- 저장 내용:
  - `MEMBER_ID`, `PERFUME_ID`, `PERFUME_NAME`, `RECOM_TYPE`, `RECOM_REASON`
  - `RECOM_REASON`은 후보의 `analysis` 문자열이 들어감

### 피드백 저장 (별도 동작)

- 프론트에서 사용자가 만족도를 누르면 호출됨
- API: `POST /layering/recommendation/feedback`
- 함수: `save_recommendation_feedback()`
- 테이블: `TB_MEMBER_MY_PERFUME_T`

## 5) 응답 생성과 반환

- 응답 스키마: `UserQueryResponse`
- 파일 위치: `C:\SKN_19\Scentence\Scentence\layering\agent\schemas.py`

성공 시 응답에 포함되는 주요 항목:

- `recommendation`: 단일 추천 결과 (최상위 후보)
- `keywords`: 분석된 키워드
- `base_perfume_id`: 감지된 베이스 향수
- `note`: 추천이 없을 때의 메시지
- `clarification_prompt`: 향수 인식 실패 시 사용자에게 물어보는 문구

### 성공 응답 예시 (추천 1건 반환)

```json
{
  "raw_text": "ck one을 가지고 있는데 더 상큼하게 변하도록 레이어링 할 수 있는 향수 추천해줘.",
  "keywords": ["citrus", "fresh"],
  "base_perfume_id": "CK_ONE_001",
  "detected_perfumes": [
    {
      "perfume_id": "CK_ONE_001",
      "perfume_name": "CK One",
      "perfume_brand": "Calvin Klein",
      "match_score": 0.91,
      "matched_text": "ck one"
    }
  ],
  "detected_pair": null,
  "recommendation": {
    "perfume_id": "CAND_021",
    "perfume_name": "Acqua di Z",
    "perfume_brand": "Brand X",
    "total_score": 0.842,
    "feasible": true,
    "feasibility_reason": null,
    "spray_order": [
      "CK One (CK_ONE_001)",
      "Acqua di Z (CAND_021)"
    ],
    "score_breakdown": {
      "base": 1.0,
      "harmony": 0.5,
      "bridge": 0.4,
      "penalty": 0.0,
      "target": 0.45
    },
    "clash_detected": false,
    "analysis": "Base 1.00 + Harmony 0.50 + Bridge 0.40 + Penalty 0.00 + Target 0.45",
    "layered_vector": [
      12.4, 9.8, 4.2, 2.1, 3.5, 0.7, 0.3, 0.0, 0.2, 0.1,
      0.0, 0.0, 0.0, 2.8, 0.1, 0.0, 0.0, 0.0, 1.6, 3.4, 0.0
    ]
  },
  "clarification_prompt": null,
  "clarification_options": [],
  "note": null,
  "save_results": [
    {
      "target": "recommendation",
      "saved": true,
      "saved_count": 1,
      "message": null
    }
  ]
}
```

### 실패 응답 예시 (향수명 인식 실패)

```json
{
  "raw_text": "상큼하게 해줘",
  "keywords": ["citrus"],
  "base_perfume_id": null,
  "detected_perfumes": [],
  "detected_pair": null,
  "recommendation": null,
  "clarification_prompt": "레이어링할 향수 이름을 알려주세요. 예: CK One, Wood Sage & Sea Salt",
  "clarification_options": [
    "CK One (Calvin Klein)",
    "Light Blue (Dolce & Gabbana)",
    "Wood Sage & Sea Salt (Jo Malone)"
  ],
  "note": "No perfume names detected from the query.",
  "save_results": []
}
```

## 6) 화면 출력 흐름

파일: `C:\SKN_19\Scentence\Scentence\frontend\app\layering\page.tsx`

1. 응답 수신 후 `result` 상태에 저장
2. 추천 결과가 있으면 채팅에 안내 메시지 추가
3. 왼쪽 패널에 추천 카드 렌더링
   - 추천 향수명/브랜드
   - 매칭 점수 (`total_score`)
   - 추천 이유 (`analysis`)
   - 분사 순서 (`spray_order`)
4. 레이어링 벡터가 유효할 경우 `AccordWheel` 컴포넌트에 전달
   - 컴포넌트 위치: `C:\SKN_19\Scentence\Scentence\frontend\components\layering\AccordWheel.tsx`

## 7) 최종 결과 요약

"ck one을 가지고 있는데 더 상큼하게 변하도록 레이어링 할 수 있는 향수 추천해줘." 요청은 다음 흐름으로 처리된다.

1. 프론트에서 `/layering/analyze`로 자연어 요청 전송
2. 백엔드에서 CK One을 베이스 향수로 감지
3. LLM 또는 휴리스틱으로 상큼함 키워드를 추출하여 타깃 벡터 생성
4. DB에서 읽어온 향수 후보들과 레이어링 점수를 계산
5. 상위 후보 1개를 추천으로 반환
6. 프론트에서 추천 카드와 어코드 원판으로 결과를 시각화

필요 시 추천 결과는 `recom_db`에 저장되며, 피드백은 별도 API로 저장된다.
