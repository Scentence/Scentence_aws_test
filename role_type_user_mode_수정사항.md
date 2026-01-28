# role_type & user_mode 연동 수정사항

## 개요

카카오 로그인 시에도 `localAuth`에 `role_type`, `user_mode` 정보가 포함되도록 수정했습니다.
이제 로컬 로그인과 카카오 로그인 모두 동일한 구조의 `localAuth`를 사용합니다.

## 수정된 파일

### 1. 백엔드: `backend/routers/users.py`

#### 변경 내용
- `/users/login` API 응답에 `user_mode` 추가
- `_get_user_mode()` 함수 추가

#### 수정된 코드

```python
# 새로 추가된 함수
def _get_user_mode(cur, member_id: int) -> str:
    """회원의 user_mode를 조회 (챗봇 응답 스타일 결정용)"""
    try:
        cur.execute(
            "SELECT user_mode FROM tb_member_basic_m WHERE member_id=%s",
            (member_id,),
        )
        row = cur.fetchone()
        if not row:
            return "BEGINNER"
        user_mode = row.get("user_mode")
        return (user_mode or "BEGINNER").upper()
    except psycopg2.errors.UndefinedColumn:
        return "BEGINNER"
```

```python
# /users/login 응답 부분 수정
role_type = _get_role_type(cur, member_id)
user_mode = _get_user_mode(cur, member_id)  # 추가됨
conn.commit()
return {
    "member_id": str(member_id),
    "nickname": nickname,
    "role_type": role_type,
    "user_mode": user_mode,  # 추가됨
}
```

---

### 2. 프론트엔드: `frontend/app/api/auth/[...nextauth]/route.ts`

#### 변경 내용
- NextAuth 콜백에서 백엔드 응답의 `role_type`, `user_mode`를 세션에 저장

#### 수정된 코드

```typescript
// signIn 콜백
user.id = data.member_id;
(user as any).roleType = data.role_type || "USER";
(user as any).userMode = data.user_mode || "BEGINNER";

// jwt 콜백
async jwt({ token, user }) {
    if (user) {
        token.id = user.id;
        token.roleType = (user as any).roleType || "USER";
        token.userMode = (user as any).userMode || "BEGINNER";
    }
    return token;
},

// session 콜백
async session({ session, token }) {
    if (session.user) {
        session.user.id = token.id as string;
        (session.user as any).roleType = token.roleType as string;
        (session.user as any).userMode = token.userMode as string;
    }
    return session;
}
```

---

### 3. 프론트엔드: `frontend/app/providers.tsx`

#### 변경 내용
- 카카오 로그인 시 `localAuth`에 `roleType`, `user_mode` 포함

#### 수정된 코드

```typescript
const localAuthData = {
    memberId: user.id,
    email: user.email || "",
    nickname: user.name || "",
    profileImage: user.image || "",
    roleType: user.roleType || "USER",      // 추가됨
    user_mode: user.userMode || "BEGINNER", // 추가됨
    provider: "kakao",
    loggedInAt: new Date().toISOString(),
};
localStorage.setItem("localAuth", JSON.stringify(localAuthData));
```

---

## 데이터 흐름

```
[카카오 로그인]
     ↓
[백엔드 /users/login]
     ↓ 응답: { member_id, nickname, role_type, user_mode }
     ↓
[NextAuth signIn 콜백]
     ↓ user 객체에 저장
     ↓
[NextAuth jwt 콜백]
     ↓ token에 저장
     ↓
[NextAuth session 콜백]
     ↓ session.user에 저장
     ↓
[providers.tsx AuthSync]
     ↓ localStorage.localAuth에 저장
     ↓
[F12 > Application > Local Storage]
     localAuth 확인 가능
```

---

## localAuth 구조

### 카카오 로그인 시
```json
{
  "memberId": "5",
  "email": "souluk319@gmail.com",
  "nickname": "김성욱",
  "profileImage": "http://k.kakaocdn.net/...",
  "roleType": "ADMIN",
  "user_mode": "BEGINNER",
  "provider": "kakao",
  "loggedInAt": "2026-01-28T..."
}
```

### 로컬 로그인 시 (기존 구조 유지)
```json
{
  "memberId": "9",
  "email": "souluk319@gmail.com",
  "nickname": "kugnus",
  "roleType": "USER",
  "user_mode": "BEGINNER",
  "loggedInAt": "2026-01-28T..."
}
```

---

## 값 설명

### role_type
| 값 | 설명 |
|---|---|
| `USER` | 일반 사용자 |
| `ADMIN` | 관리자 |

### user_mode
| 값 | 설명 |
|---|---|
| `BEGINNER` | 초보자 모드 - 챗봇이 더 친절하고 자세하게 설명 |
| `EXPERT` | 전문가 모드 - 챗봇이 간결하게 응답 |

---

## 테스트 방법

1. Docker 재시작
   ```bash
   docker-compose down && docker-compose up --build
   ```

2. 카카오 로그인 후 F12 > Application > Local Storage 확인
   - `localAuth` 키에 `roleType`, `user_mode` 포함되어 있는지 확인

3. 챗봇 페이지에서 대화 시 `user_mode`가 백엔드로 전달되는지 확인
   - 백엔드 로그에서 `user_mode` 값 확인
