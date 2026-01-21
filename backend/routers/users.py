from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import re
import psycopg2.extras
from .user import get_user_db_connection
from passlib.context import CryptContext

# 이 라우터는 '/users'로 시작하는 모든 요청을 처리합니다.
router = APIRouter(prefix="/users", tags=["users"])

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


# [요청 모델] 프론트엔드(NextAuth)에서 보내주는 데이터 형식 정의
class KakaoLoginRequest(BaseModel):
    kakao_id: str  # 카카오 고유 ID (필수)
    nickname: Optional[str] = None  # NULL 허용
    email: Optional[str] = None  # NULL 허용
    profile_image: Optional[str] = None


class LocalRegisterRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    sex: Optional[str] = None  # 'M' or 'F'
    req_agr_yn: Optional[str] = "N"


class LocalLoginRequest(BaseModel):
    email: str
    password: str


# [API] 카카오 로그인 처리 (POST /users/login)
# 1. 이미 가입된 회원이면 -> 회원 번호 반환 (로그인 성공)
# 2. 처음 온 회원이면 -> DB에 정보 저장 후 -> 회원 번호 반환 (회원가입 성공)
@router.post("/login")
def login_with_kakao(req: KakaoLoginRequest):
    conn = get_user_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # [1단계] 가입 이력 조회
        # TB_MEMBER_AUTH_T 테이블에서 'KAKAO' + '사용자ID' 조합이 있는지 확인합니다.
        cur.execute(
            "SELECT member_id FROM tb_member_auth_t WHERE provider='KAKAO' AND provider_user_id=%s",
            (req.kakao_id,),
        )
        existing_auth = cur.fetchone()

        member_id = None

        if existing_auth:
            # [A] 이미 가입된 유저인 경우
            member_id = existing_auth["member_id"]
            print(f"✅ 기존 회원 로그인 성공: 회원번호 {member_id}")

        else:
            # [B] 신규 회원가입 (3단계 Insert)
            # 우리 DB는 데이터 정규화를 위해 3개의 테이블로 쪼개져 있습니다.

            # 1. 기본 계정 생성 (TB_MEMBER_BASIC_M)
            # - 역할: 시스템 내부 관리용 계정 생성
            login_id_gen = f"kakao_{req.kakao_id}"
            sql_basic = """
                INSERT INTO tb_member_basic_m 
                (login_id, pwd_hash, join_channel, sns_join_yn, email_alarm_yn, sns_alarm_yn)
                VALUES (%s, %s, 'KAKAO', 'Y', 'N', 'N')
                RETURNING member_id
            """
            cur.execute(sql_basic, (login_id_gen, "KAKAO_NO_PASS"))
            member_id = cur.fetchone()["member_id"]  # 방금 생성된 회원번호(PK) 가져오기

            # 2. 프로필 정보 저장 (TB_MEMBER_PROFILE_T)
            # - 역할: 닉네임, 이메일 등 사용자에게 보여지는 정보 저장
            sql_profile = """
                INSERT INTO tb_member_profile_t
                (member_id, nickname, email, sns_id)
                VALUES (%s, %s, %s, %s)
            """
            cur.execute(sql_profile, (member_id, req.nickname, req.email, req.kakao_id))

            # 3. 인증 연결 정보 저장 (TB_MEMBER_AUTH_T)
            # - 역할: '이 회원은 카카오로 로그인한다'는 연결고리 저장
            sql_auth = """
                INSERT INTO tb_member_auth_t 
                (member_id, provider, provider_user_id, email)
                VALUES (%s, 'KAKAO', %s, %s)
            """
            cur.execute(sql_auth, (member_id, req.kakao_id, req.email))

            print(f"🎉 신규 회원가입 완료: 회원번호 {member_id}")

        conn.commit()  # 모든 DB 변경사항 확정 (저장)
        return {"member_id": str(member_id), "nickname": req.nickname}

    except Exception as e:
        conn.rollback()  # 에러 발생 시 모든 작업 취소 (데이터 오염 방지)
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.post("/login/local")
def login_local_user(req: LocalLoginRequest):
    conn = get_user_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute(
            "SELECT member_id, pwd_hash FROM tb_member_auth_t WHERE provider='LOCAL' AND provider_user_id=%s",
            (req.email,),
        )
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not row.get("pwd_hash"):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not pwd_context.verify(req.password, row["pwd_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return {"member_id": str(row["member_id"])}

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.post("/register")
def register_local_user(req: LocalRegisterRequest):
    if req.req_agr_yn not in ("Y", "N"):
        raise HTTPException(status_code=400, detail="Invalid agreement value")

    if req.req_agr_yn != "Y":
        raise HTTPException(status_code=400, detail="Required agreements not accepted")

    if req.sex and req.sex not in ("M", "F"):
        raise HTTPException(status_code=400, detail="Invalid sex value")

    password = req.password
    if not password:
        raise HTTPException(status_code=400, detail="Password is required")

    if len(password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters"
        )

    allowed_specials_only = bool(re.fullmatch(r"[A-Za-z0-9!@#$%]+", password))
    has_lower = any(ch.islower() for ch in password)
    has_upper = any(ch.isupper() for ch in password)
    has_number = any(ch.isdigit() for ch in password)
    has_special = any(ch in "!@#$%" for ch in password)

    if not allowed_specials_only:
        raise HTTPException(
            status_code=400,
            detail="Password must use only letters, numbers, and !@#$%",
        )
    if not (has_lower and has_upper and has_number and has_special):
        raise HTTPException(
            status_code=400,
            detail="Password must include upper, lower, number, special",
        )

    conn = get_user_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute(
            "SELECT member_id FROM tb_member_basic_m WHERE login_id=%s", (req.email,)
        )
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Login ID already exists")

        cur.execute(
            "SELECT auth_id FROM tb_member_auth_t WHERE provider='LOCAL' AND provider_user_id=%s",
            (req.email,),
        )
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Local account already exists")

        pwd_hash = pwd_context.hash(password)

        sql_basic = """
            INSERT INTO tb_member_basic_m
            (login_id, pwd_hash, join_channel, sns_join_yn, email_alarm_yn, sns_alarm_yn)
            VALUES (%s, %s, 'LOCAL', 'N', 'N', 'N')
            RETURNING member_id
        """
        cur.execute(sql_basic, (req.email, pwd_hash))
        member_id = cur.fetchone()["member_id"]

        sql_profile = """
            INSERT INTO tb_member_profile_t
            (member_id, name, sex, email)
            VALUES (%s, %s, %s, %s)
        """
        cur.execute(sql_profile, (member_id, req.name, req.sex, req.email))

        sql_auth = """
            INSERT INTO tb_member_auth_t
            (member_id, provider, provider_user_id, email, pwd_hash)
            VALUES (%s, 'LOCAL', %s, %s, %s)
        """
        cur.execute(sql_auth, (member_id, req.email, req.email, pwd_hash))

        sql_status = """
            INSERT INTO tb_member_status_t
            (member_id, member_status)
            VALUES (%s, 'NORMAL')
        """
        cur.execute(sql_status, (member_id,))

        conn.commit()
        return {"member_id": str(member_id)}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()
