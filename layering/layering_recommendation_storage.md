# 레이어링 추천 결과 저장 설계

이 문서는 레이어링 API가 추천 결과를 `recom_db`에 저장하는 흐름과
응답 구조를 정의한다.

## 저장 대상 테이블

- `recom_db.TB_MEMBER_RECOM_RESULT_T`
  - 저장 조건: `member_id`가 존재하고 `save_recommendations=true`
- `recom_db.TB_MEMBER_MY_PERFUME_T`
  - 저장 조건: `member_id`가 존재하고 `save_my_perfume=true`

## 요청 필드 (추가)

### `/layering/analyze`
```json
{
  "user_text": "CK One 있는데 시트러스 레이어링 추천해줘",
  "member_id": 5,
  "save_recommendations": true,
  "save_my_perfume": false
}
```

### `/layering/recommend`
```json
{
  "base_perfume_id": "789",
  "keywords": ["citrus"],
  "member_id": 5,
  "save_recommendations": true,
  "save_my_perfume": true
}
```

## 응답 필드 (추가)

모든 레이어링 응답에는 `save_results` 배열이 포함된다.
저장 성공/실패 여부와 대상 테이블을 명확히 전달한다.

```json
{
  "save_results": [
    {
      "target": "recommendation",
      "saved": true,
      "saved_count": 1,
      "message": null
    },
    {
      "target": "my_perfume",
      "saved": false,
      "saved_count": 0,
      "message": "already exists"
    }
  ]
}
```

### save_results 필드 정의

- `target`: `"recommendation"` 또는 `"my_perfume"`
- `saved`: 저장 성공 여부
- `saved_count`: 저장된 행 수
- `message`: 실패/상태 메시지

## 테이블 매핑 규칙

### TB_MEMBER_RECOM_RESULT_T

- `MEMBER_ID` = 요청 `member_id`
- `PERFUME_ID` = 추천 후보 `perfume_id`
- `PERFUME_NAME` = 추천 후보 `perfume_name`
- `RECOM_TYPE` = `"LAYERING"`
- `RECOM_REASON` = 추천 후보 `analysis` (없으면 기본 메시지)
- `INTEREST_YN` = `"N"`

### TB_MEMBER_MY_PERFUME_T

- `MEMBER_ID` = 요청 `member_id`
- `PERFUME_ID` = 베이스 향수 `perfume_id`
- `PERFUME_NAME` = 베이스 향수 `perfume_name`
- `REGISTER_STATUS` = `"RECOMMENDED"`
- `PREFERENCE` = `"NEUTRAL"` 기본값, 만족도 피드백으로 갱신

### 추천 만족도 피드백

추천 카드에서 만족도를 선택하면 `TB_MEMBER_MY_PERFUME_T`에 저장된다.

- 요청 경로: `POST /layering/recommendation/feedback`
- `REGISTER_STATUS` = `"RECOMMENDED"`
- `PREFERENCE` = `"GOOD" | "BAD" | "NEUTRAL"`

## 주의사항

- 저장 실패가 있어도 API 응답 자체는 200으로 유지하며, 실패 정보는
  `save_results.message`로 전달한다.
- `member_id`가 없으면 저장을 시도하지 않는다.

## 로그 확인

레이어링 컨테이너 로그에서 저장 요청 및 결과를 확인할 수 있다.

- `Layering analyze request received ...`
- `Connecting to recom_db (dbname=...)`
- `Recommendation save completed ...`
- `My perfume save completed ...`
- `Recommendation feedback save completed ...`
