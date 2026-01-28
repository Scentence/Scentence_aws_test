# 향수 삭제 로직 고도화 계획 (Deletion Logic Master Plan)

## 1. 개요
사용자가 향수를 보관함에서 제거할 때, **'경험으로 남길지(Archive)'** 아니면 **'완전히 지울지(Remove)'** 선택할 수 있는 기능을 구현합니다.

## 2. 두 가지 삭제 방식 (Two Ways to Delete)

| 방식 | 버튼 (UI) | 동작 원리 (Logic) | API Method | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **1. 기록 남기기**<br>(Soft Delete) | **[좋음/무난/별로]**<br>평가 버튼 클릭 | 상태를 `HAVE` → `HAD`로 변경<br>+ 선호도(`Preference`) 저장 | `PATCH` | **(기본 추천)**<br>취향 분석 데이터로 활용됨 |
| **2. 흔적 없이 삭제**<br>(Hard Delete) | **[기록 없이 삭제]**<br>텍스트 버튼 클릭 | DB에서 해당 향수 데이터를<br>**영구적으로 제거** | `DELETE` | **(신규 추가)**<br>잘못 등록했을 때 사용 |

## 3. 구현 상세 (Implementation Details)

### [수정] `Frontend/components/archives/PerfumeDetailModal.tsx`
- **현재**: 평가 버튼 3개만 존재 (👍, 😐, 👎)
- **추가**: 평가 목록 하단에 **"기록 없이 영구 삭제하기"**라는 작고 회색 처리된 텍스트 버튼 추가.
- **동작**: 클릭 시 `onDelete(id, undefined)`를 호출하여, frontend [handleDelete](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence-app/frontend/app/archives/page_backup.tsx#63-68) 함수의 `else` 블록(완전 삭제)을 실행.

### [확인] `Frontend/app/archives/page.tsx`
- 이미 `rating`이 없을 경우(`undefined`) `DELETE` API를 호출하도록 구현되어 있어 **수정 불필요**. (API 연동만 확인)

### [확인] `Backend/routers/users.py`
- `DELETE` Endpoint가 이미 구현되어 있으며, 연결 누수 문제도 해결되어 있어 **수정 불필요**.

## 4. 작업 순서
1. [PerfumeDetailModal.tsx](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence-app/frontend/components/archives/PerfumeDetailModal.tsx)에 "완전 삭제" 버튼 UI 추가.
2. 버튼 핸들러 연결 (`onDelete` 호출 시 rating 인자 없이 호출).
