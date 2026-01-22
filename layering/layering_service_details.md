# Layering 서비스 세부 동작 정리

본 문서는 `Scentence/layering` 폴더에 구현된 FastAPI 레이어링 서비스가 어떻게 입력을 받아 처리하고, 추천 점수를 계산해 응답을 생성하는지 한국어로 정리한다. 모든 내용은 현재 리포지토리의 코드(2026-01-22 기준)를 근거로 한다.

## 1. 입력은 누가 보내고 어디서 처리되나?
- 사용자는 HTTP 클라이언트(웹 프론트엔드, 다른 서비스 등)를 통해 `POST /layering/recommend` 엔드포인트로 JSON을 전송한다. 이 엔드포인트는 `layering/main.py` 42~65줄의 `layering_recommend()` 함수로 정의되어 있다.
- FastAPI는 요청 바디를 `LayeringRequest` 모델( `agent/schemas.py` 62~65줄)로 파싱한다. 필수 필드는 `base_perfume_id`, 선택 필드는 문자열 목록인 `keywords`이다.
- 파싱된 `LayeringRequest` 인스턴스는 그대로 `rank_recommendations()` 호출에 전달되어 내부 알고리즘에서 사용 가능한 형태(파이썬 객체)로 이미 변환된 상태가 된다. 추가 전처리는 `LayeringRequest`의 Pydantic 유효성 검사에서 처리된다.

## 2. `base_perfume_id`란?
- `base_perfume_id`는 사용자가 현재 뿌리고 있는 기본 향수를 식별하는 문자열이다. `PerfumeRepository.get_perfume()` (`agent/database.py` 97~102줄)이 이 ID를 사용해 사전에 로드한 `PerfumeVector`를 검색한다.
- FastAPI 엔드포인트에서 `base_perfume_id`가 잘못되면 `get_perfume()`이 `KeyError`를 발생시키고, `main.py` 44~52줄에서 404 HTTP 오류로 변환해 사용자에게 “Perfume '...' not found” 메시지를 돌려준다.

## 3. `get_target_vector()`는 어떤 입력을 어떻게 해석하나?
- 위치: `agent/tools.py` 20~34줄.
- 입력: 문자열 시퀀스(`keywords`). 각 키워드는 소문자+trim 처리 후 `agent/constants.py`의 `KEYWORD_MAP`에서 향 계열 목록으로 매핑된다. 예: "warm" → `["Oriental", "Spicy", "Resinous"]`.
- 처리: 해당 향 계열의 인덱스를 찾아 `KEYWORD_VECTOR_BOOST`(30.0)을 누적해 목표 벡터를 만든다. 정의되지 않은 키워드는 무시한다.
- 결과: `ACCORDS` 크기(21)의 리스트. 이후 `_target_match_score()`가 이 벡터를 사용해 후보 조합이 사용자 의도에 얼마나 맞는지 계산한다.

## 4. `harmony_score`와 `bridge`는 어떻게 계산하나?
- `harmony_score`: `_harmony_score()` (`agent/tools.py` 95~111줄)가 베이스/후보 향수의 BASE 노트 목록(`base_notes`)을 비교한다. `TB_PERFUME_NOTES_M.csv`의 `TYPE=BASE` 값을 읽어 집합으로 만든 뒤, 교집합/합집합 비율(Jaccard 유사도)을 계산한다.
  - 유사도 0 → 0점, 0.4~0.7 → +1.0, 0.7 초과 → +0.5. BASE 노트가 일정 부분 겹치면 보너스를 주는 규칙이다.
- `bridge` 보너스: `_bridge_bonus()` (`agent/tools.py` 106~112줄)가 두 전체 벡터에서 모두 5~15 사이인 노트를 찾을 때마다 +0.4씩 더한다. 공통된 중간 강도의 노트가 많을수록 브릿지 점수가 커진다.
- 이 두 값은 `ScoreBreakdown`(`agent/schemas.py` 67~73줄)에 저장되어 응답으로 되돌아간다.

## 5. `reason`은 무엇을 받아 무엇을 출력하나?
- **Feasibility reason**: `_feasibility_guard()` (`agent/tools.py` 131~152줄)가 타깃 벡터와의 정렬도를 검사한다. 기준 이하(0.6 미만)이거나 키워드와 베이스가 충돌하면 `(False, "원인")`을 반환한다. 하지만 `rank_recommendations()` 74~77줄에서 `feasible`이 `False`인 결과는 응답에 포함되기 전에 필터링되므로, 현재 사용자에게는 전달되지 않는다. `LayeringCandidate.feasibility_reason` 필드가 모델에 존재하지만, 실제 응답에서는 항상 `None`이며 원인은 내부 진단용으로만 쓰인다.
- **Analysis string**: `_result_to_candidate()` (`agent/tools.py` 192~206줄)이 `_build_analysis_string()`(218~229줄)을 호출해 "Base 1.00 + Harmony 1.00 + ..." 형태의 설명을 만든다. 입력은 `ScoreBreakdown`이며 각 항목을 소수점 2자리로 포맷해 연결한다. 사용자는 이 문자열을 통해 총점이 어떻게 구성됐는지 알 수 있다.

## 6. `spray_order`의 candidate는 어떻게 만들어지나?
- `_spray_order()` (`agent/tools.py` 181~189줄)는 베이스와 후보 `PerfumeVector`의 `persistence_score`를 비교한다.
- 지속력이 높은 향수를 먼저 뿌리도록 결정한 후, "향수명 (ID)" 형식의 문자열 두 개로 리스트를 반환한다. 이 결과는 `LayeringCandidate.spray_order`(`agent/schemas.py` 82~83줄)에 저장된다.

## 7. `rank_recommendations()` 상세 동작
- 정의: `agent/tools.py` 65~80줄.
- 단계
  1. `PerfumeRepository.get_perfume(base_perfume_id)`로 베이스 벡터를 가져온다.
  2. `get_target_vector(keywords)`로 타깃 벡터를 계산한다.
  3. `repository.all_candidates(exclude_id=base_perfume_id)`로 전체 후보를 순회하며 `calculate_advanced_layering()`을 실행한다. 이 함수는 clash 판정, harmony, bridge, target score, penalty, spray order, feasibility를 하나의 `LayeringComputationResult`로 묶는다.
  4. `feasible`이 `False`면 제외하고, 나머지는 `_result_to_candidate()`로 `LayeringCandidate`로 변환한다.
  5. 총점(`total_score`) 기준 내림차순 정렬 후 상위 3개만 반환하며, 전체 가능 후보 수는 `total_available`로 별도 제공한다.

## 8. `LayeringRequest` 동작
- 위치: `agent/schemas.py` 62~65줄.
- FastAPI가 요청 JSON을 받을 때 Pydantic이 `base_perfume_id`(필수 문자열)와 `keywords`(기본 빈 리스트)를 검증한다.
- 잘못된 타입이나 누락 시 FastAPI가 자동으로 422 응답을 보내므로, 서비스 내부에서는 신뢰할 수 있는 데이터만 다루게 된다.

## 참고 파일 요약
- `layering/main.py`: API 엔드포인트 정의/예외 처리.
- `layering/agent/database.py`: `PerfumeRepository`와 벡터화 로직.
- `layering/agent/tools.py`: 추천 알고리즘 전체(타깃 벡터, 스코어링, 정렬 등).
- `layering/agent/schemas.py`: 요청/응답 데이터 모델.
- `layering/agent/constants.py`: 향 계열, 키워드 매핑, 충돌 규칙.

이 문서를 통해 레이어링 서비스의 입력 처리부터 추천 산출까지의 흐름을 전체적으로 이해할 수 있다.
