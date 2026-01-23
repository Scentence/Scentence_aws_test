# Layering Error Handling Guide

## 목적
레이어링 서비스에서 발생하는 오류를 단계별로 구분하고, 프론트에서 사용자에게 명확하게 안내하기 위한 에러 구조를 정리한다.

## 에러 응답 형식
FastAPI는 `HTTPException`의 `detail`에 아래 구조를 담아 응답한다.

```json
{
  "detail": {
    "error": {
      "code": "DB_CONNECTION_FAILED",
      "message": "DB 연결에 실패했습니다.",
      "step": "db_connect",
      "retriable": true,
      "details": "..."
    }
  }
}
```

## 단계(step) 정의
- `db_connect`: DB 연결
- `data_load`: DB 조회/데이터 적재
- `analysis`: 자연어 분석
- `perfume_lookup`: 향수 식별
- `ranking`: 추천 계산

## 에러 코드
- `DB_CONNECTION_FAILED`: DB 연결 실패
- `DB_QUERY_FAILED`: DB 조회 실패
- `DATASET_EMPTY`: 향수 데이터 없음
- `ANALYSIS_FAILED`: 자연어 분석 실패
- `RANKING_FAILED`: 추천 계산 실패
- `PERFUME_NOT_FOUND`: 요청한 향수 ID 없음

## 프론트 표시 가이드
- `step`에 따라 사용자에게 원인과 조치(서버/DB 상태 확인 등)를 안내한다.
- `details`는 `LAYERING_DEBUG_ERRORS=true` 설정 시에만 응답에 포함된다.
- 프론트는 `NEXT_PUBLIC_LAYERING_DEBUG_ERRORS=true` 또는 개발 모드일 때만 `details`를 표시한다.

## DB 연결 설정
아래 환경 변수를 사용해 DB 접속 정보를 설정한다.

- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
