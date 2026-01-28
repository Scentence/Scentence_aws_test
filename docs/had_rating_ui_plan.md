# 경험(HAD) 상태 UI 고도화 (Rating UI Plan)

## 1. 개요
사용자가 '경험(HAD)' 상태인 향수를 볼 때는, 이미 사용해본 향수이므로 상태 변경보다는 **'어땠는지(Rating)'**를 기록하는 것이 주된 목적입니다. 따라서 HAD 상태일 때는 상태 변경 버튼 대신 **평가 버튼**을 보여주도록 UI를 개편합니다.

## 2. 변경 전/후 비교

| 상태 | 기존 UI (Present) | 변경된 UI (To-Be) |
| :--- | :--- | :--- |
| **HAVE / WISH** | [보유] [경험] [위시] | [보유] [경험] [위시] (기존 유지) |
| **HAD** (경험) | [보유] [경험] [위시] | **[👍 좋음] [😐 무난] [👎 별로]**<br>*(상태 변경이 필요할 경우 별도 텍스트 버튼 제공)* |

## 3. 상세 구현 계획

### [MODIFY] [frontend/app/archives/page.tsx](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence-app/frontend/app/archives/page.tsx)
- **`handleUpdatePreference(id, preference)` 함수 추가**:
    - Backend API `PATCH` 호출 (`register_status="HAD"`, `preference=새로 선택한 값`).
    - Collection 및 SelectedPerfume 상태 업데이트.

### [MODIFY] [frontend/components/archives/PerfumeDetailModal.tsx](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence-app/frontend/components/archives/PerfumeDetailModal.tsx)
- **조건부 렌더링**: `perfume.status === 'HAD'` 체크.
- **Rate Button Group**:
    - GOOD (👍 좋았어요) - Green
    - NEUTRAL (😐 무난해요) - Gray
    - BAD (👎 별로예요) - Red
    - 현재 저장된 `preference` 상태에 따라 버튼 활성화(Highlight).
- **상태 변경 옵션**: "다시 보유하게 되었나요? (상태 변경)" 링크를 하단에 배치하여 실수로 HAD로 보낸 경우 복구 가능하게 함.

## 4. 데이터 매핑
- GOOD: `preference = 'GOOD'`
- NEUTRAL: `preference = 'NEUTRAL'`
- BAD: `preference = 'BAD'`
