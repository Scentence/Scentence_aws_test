# AI Agent 팀 작업 요청서

> **요청 내용:** 추천 향수 저장 기능을 위해 `perfume_id` 응답 추가
>
> **예상 작업량:** 코드 1줄 수정
>
> **긴급도:** 낮음 (프론트/백엔드 작업 완료 후 연동)

---

## 왜 필요한가?

```
현재 플로우:
유저 → 챗봇 추천 → 끝 (데이터 없음, 재방문 없음)

개선 플로우:
유저 → 챗봇 추천 → [저장] → My Archives → 재방문 → 구매
                      ↑
                 여기에 perfume_id 필요
```

**추천만 하고 끝나면 서비스 가치 = 0**

저장 기능이 있어야:
- 유저가 다시 돌아옴
- 어떤 추천이 실제로 저장되는지 데이터 수집
- 개인화 추천 품질 향상 가능

---

## 해야 할 일 (1가지)

### `backend/agent/schemas.py` 수정

**Before:**
```python
class PerfumeDetail(BaseModel):
    perfume_name: str
    perfume_brand: str
    accord: str
    season: str
    occasion: str
    gender: str
    notes: PerfumeNotes
    image_url: Optional[str]
```

**After:**
```python
class PerfumeDetail(BaseModel):
    perfume_id: int           # ← 이거 하나 추가
    perfume_name: str
    perfume_brand: str
    accord: str
    season: str
    occasion: str
    gender: str
    notes: PerfumeNotes
    image_url: Optional[str]
```

**끝.**

---

## 안 해도 되는 것들

| 작업 | 필요 여부 |
|------|----------|
| 프롬프트 수정 | ❌ 안 해도 됨 |
| `[REGISTER:id]` 태그 출력 | ❌ 안 해도 됨 |
| graph.py 수정 | ❌ 안 해도 됨 (이미 id 가져오는 중) |
| 새 API 개발 | ❌ 백엔드팀이 함 |
| UI 개발 | ❌ 프론트팀이 함 |

---

## Q&A

**Q: perfume_id가 왜 필요함?**

A: 프론트에서 "저장" 버튼 누르면 백엔드 API 호출해야 하는데,
   향수 이름만으로는 정확한 매칭이 안 됨. ID가 있어야 확실함.

**Q: 이미 DB에서 id 가져오고 있지 않음?**

A: 맞음. `database.py`에서 `perfume_id` 가져오는데
   `PerfumeDetail` 스키마에 없어서 버려지고 있음.
   스키마에 필드 추가하면 자동으로 포함됨.

**Q: 나중에 해도 됨?**

A: 됨. 프론트/백엔드 작업 먼저 진행하고,
   챗봇 연동은 마지막에 해도 문제없음.

---

## 작업 완료 후 테스트

챗봇 응답에 `perfume_id`가 포함되는지 확인:

```json
{
  "perfume_id": 123,
  "perfume_name": "Bleu de Chanel",
  "perfume_brand": "Chanel",
  ...
}
```

---

## 연락처

질문 있으면 말해주세요!
