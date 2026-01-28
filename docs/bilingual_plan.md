# 한/영 자동 변환 시스템 (Bilingual Switch)

## 1. 개요
대부분의 한국 사용자가 향수를 '한글'로 검색하고 기억한다는 점을 반영하여, 아카이브 된 향수들의 이름을 **한글(`name_kr`) ↔ 영어([name](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence-app/backend/routers/users.py#426-451))** 로 자유롭게 전환할 수 있는 기능을 추가합니다.

## 2. 구현 상세

### [Step 1] Backend ([users.py](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence-app/backend/routers/users.py))
- **[get_my_perfumes](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence-app/backend/routers/users.py#936-1010) 수정**:
    - [perfume_db](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence-app/backend/routers/perfumes.py#39-42) 조회 쿼리에 **`perfume_name_kr`** 컬럼 추가.
    - 응답 데이터(`merged`)에 `name_kr` 필드 포함.

### [Step 2] Frontend ([page.tsx](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence-app/frontend/app/archives/page.tsx))
- **State 추가**: `const [isKorean, setIsKorean] = useState(true);` (기본값: 한글)
- **Toggle UI**: 메인 헤더 또는 탭 영역 우측에 `[한글 / ENG]` 토글 버튼 배치.
- **Props 전달**: [CabinetShelf](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence-app/frontend/components/archives/CabinetShelf.tsx#18-77) 및 [PerfumeDetailModal](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence-app/frontend/components/archives/PerfumeDetailModal.tsx#24-238)에 `isKorean` 상태 전달.

### [Step 3] Components ([CabinetShelf](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence-app/frontend/components/archives/CabinetShelf.tsx#18-77), [Modal](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence-app/frontend/components/archives/PerfumeDetailModal.tsx#24-238))
- **이름 렌더링 로직 변경**:
  ```tsx
  const displayName = (isKorean && perfume.name_kr) ? perfume.name_kr : perfume.name;
  ```
- **브랜드명**: 브랜드도 한글 데이터가 있다면 좋겠지만, 없다면 영문 유지. (우선 이름부터 적용)

## 3. 예상 UI
- **Toggle Button**: `🌐 언어: 한국어` ↔ `🌐 Language: English`
- 클릭 시 화면 내 모든 향수 카드의 이름이 즉시 번역된 것처럼 바뀜.
