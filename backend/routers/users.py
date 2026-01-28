from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import re
import psycopg2.extras
import psycopg2.errors
from .user import get_user_db_connection
from passlib.context import CryptContext
import os
import uuid
import shutil
from datetime import datetime, timedelta
from agent.database import add_my_perfume

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
    phone_no: Optional[str] = None
    address: Optional[str] = None
    nickname: Optional[str] = None
    user_mode: Optional[str] = None  # 'BEGINNER' or 'EXPERT'
    req_agr_yn: Optional[str] = "N"
    email_alarm_yn: Optional[str] = "N"
    sns_alarm_yn: Optional[str] = "N"


class LocalLoginRequest(BaseModel):
    email: str
    password: str


class UpdateProfileRequest(BaseModel):
    nickname: Optional[str] = None
    profile_image_url: Optional[str] = None
    name: Optional[str] = None
    sex: Optional[str] = None
    phone_no: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    sub_email: Optional[str] = None
    sns_join_yn: Optional[str] = None
    email_alarm_yn: Optional[str] = None
    sns_alarm_yn: Optional[str] = None


class UpdatePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


# [API] 카카오 로그인 처리 (POST /users/login)
# 1. 이미 가입된 회원이면 -> 회원 번호 반환 (로그인 성공)
# 2. 처음 온 회원이면 -> DB에 정보 저장 후 -> 회원 번호 반환 (회원가입 성공)
@router.post("/login")
def login_with_kakao(req: KakaoLoginRequest):
    conn = get_user_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        _ensure_profile_columns(cur)
        nickname = req.nickname or "향수초보"
        profile_image_url = req.profile_image or None
        # [1단계] 가입 이력 조회
        # TB_MEMBER_PROFILE_T.sns_id + TB_MEMBER_BASIC_M.join_channel 조합으로 확인합니다.
        cur.execute(
            """
            SELECT b.member_id
            FROM tb_member_basic_m b
            JOIN tb_member_profile_t p ON b.member_id = p.member_id
            WHERE b.join_channel = 'KAKAO' AND p.sns_id = %s
            """,
            (req.kakao_id,),
        )
        existing_auth = cur.fetchone()

        member_id = None

        if existing_auth:
            # [A] 이미 가입된 유저인 경우
            member_id = existing_auth["member_id"]
            print(f"✅ 기존 회원 로그인 성공: 회원번호 {member_id}")

            status_check = _check_withdraw_status(cur, member_id)
            if status_check["status"] == "WITHDRAW_REQ":
                return {
                    "member_id": str(member_id),
                    "withdraw_pending": True,
                    "nickname": req.nickname,
                }
            if status_check["status"] == "DELETED":
                conn.commit()
                raise HTTPException(status_code=410, detail="Account deleted")

            if nickname or profile_image_url:
                cur.execute(
                    "SELECT nickname, profile_image_url FROM tb_member_profile_t WHERE member_id=%s",
                    (member_id,),
                )
                profile_row = cur.fetchone()
                if profile_row:
                    if not profile_row.get("nickname") and nickname:
                        cur.execute(
                            "UPDATE tb_member_profile_t SET nickname=%s WHERE member_id=%s",
                            (nickname, member_id),
                        )
                    if not profile_row.get("profile_image_url") and profile_image_url:
                        cur.execute(
                            "UPDATE tb_member_profile_t SET profile_image_url=%s WHERE member_id=%s",
                            (profile_image_url, member_id),
                        )

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
                (member_id, nickname, email, sns_id, profile_image_url)
                VALUES (%s, %s, %s, %s, %s)
            """
            cur.execute(sql_profile, (member_id, nickname, req.email, req.kakao_id, profile_image_url))

            sql_status = """
                INSERT INTO tb_member_status_t
                (member_id, member_status)
                VALUES (%s, 'NORMAL')
            """
            cur.execute(sql_status, (member_id,))

            print(f"🎉 신규 회원가입 완료: 회원번호 {member_id}")

        role_type = _get_role_type(cur, member_id)
        conn.commit()  # 모든 DB 변경사항 확정 (저장)
        return {
            "member_id": str(member_id),
            "nickname": nickname,
            "role_type": role_type,
        }

    except Exception as e:
        conn.rollback()  # 에러 발생 시 모든 작업 취소 (데이터 오염 방지)
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


def _ensure_profile_columns(cur):
    cur.execute(
        "ALTER TABLE tb_member_profile_t ADD COLUMN IF NOT EXISTS sub_email VARCHAR(100)"
    )
    cur.execute(
        "ALTER TABLE tb_member_profile_t ADD COLUMN IF NOT EXISTS profile_image_url VARCHAR(255)"
    )


def _get_role_type(cur, member_id: int) -> str:
    try:
        cur.execute(
            "SELECT role_type FROM tb_member_basic_m WHERE member_id=%s",
            (member_id,),
        )
        row = cur.fetchone()
        if not row:
            return "USER"
        role_type = row.get("role_type")
        return (role_type or "USER").upper()
    except psycopg2.errors.UndefinedColumn:
        return "USER"


def _is_admin_member(cur, member_id: int) -> bool:
    return _get_role_type(cur, member_id) == "ADMIN"


def _ensure_admin_by_member_id(cur, member_id: int):
    if not _is_admin_member(cur, member_id):
        raise HTTPException(status_code=403, detail="Admin access required")


def _check_withdraw_status(cur, member_id: int):
    cur.execute(
        "SELECT member_status, alter_dt FROM tb_member_status_t WHERE member_id=%s",
        (member_id,),
    )
    status_row = cur.fetchone()
    if not status_row or status_row.get("member_status") != "WITHDRAW_REQ":
        return {"status": "NORMAL"}

    alter_dt = status_row.get("alter_dt")
    if alter_dt and isinstance(alter_dt, datetime):
        if alter_dt < datetime.utcnow() - timedelta(days=7):
            cur.execute(
                "DELETE FROM tb_member_basic_m WHERE member_id=%s", (member_id,)
            )
            return {"status": "DELETED"}

    return {"status": "WITHDRAW_REQ"}


def _validate_password(password: str):
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


@router.post("/login/local")
def login_local_user(req: LocalLoginRequest):
    conn = get_user_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute(
            """
            SELECT member_id, pwd_hash, role_type
            FROM tb_member_basic_m
            WHERE login_id=%s AND join_channel='LOCAL'
            """,
            (req.email,),
        )
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not row.get("pwd_hash"):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not pwd_context.verify(req.password, row["pwd_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        status_check = _check_withdraw_status(cur, row["member_id"])
        if status_check["status"] == "WITHDRAW_REQ":
            return {
                "member_id": str(row["member_id"]),
                "withdraw_pending": True,
            }
        if status_check["status"] == "DELETED":
            conn.commit()
            raise HTTPException(status_code=410, detail="Account deleted")

        return {
            "member_id": str(row["member_id"]),
            "role_type": (row.get("role_type") or "USER").upper(),
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/check-email")
def check_email(email: str):
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    conn = get_user_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute(
            "SELECT member_id FROM tb_member_basic_m WHERE login_id=%s", (email,)
        )
        exists = cur.fetchone() is not None
        return {"available": not exists}
    except Exception as e:
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

    if req.email_alarm_yn not in ("Y", "N"):
        raise HTTPException(status_code=400, detail="Invalid email alarm value")

    if req.user_mode and req.user_mode not in ("BEGINNER", "EXPERT"):
        raise HTTPException(status_code=400, detail="Invalid user mode")

    password = req.password
    _validate_password(password)

    conn = get_user_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute(
            "SELECT member_id FROM tb_member_basic_m WHERE login_id=%s", (req.email,)
        )
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Login ID already exists")

        pwd_hash = pwd_context.hash(password)

        sql_basic = """
            INSERT INTO tb_member_basic_m
            (login_id, pwd_hash, join_channel, sns_join_yn, email_alarm_yn, sns_alarm_yn, role_type)
            VALUES (%s, %s, 'LOCAL', 'N', %s, %s, %s)
            RETURNING member_id
        """
        cur.execute(sql_basic, (req.email, pwd_hash, req.email_alarm_yn, req.sns_alarm_yn, req.user_mode))
        member_id = cur.fetchone()["member_id"]

        sql_profile = """
            INSERT INTO tb_member_profile_t
            (member_id, name, nickname, sex, email, phone_no, address)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(sql_profile, (member_id, req.name, req.nickname or req.name, req.sex, req.email, req.phone_no, req.address))

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


@router.get("/profile/{member_id}")
def get_profile(member_id: int):
    conn = get_user_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        _ensure_profile_columns(cur)
        cur.execute(
            """
            SELECT
                b.member_id,
                b.role_type,
                b.join_channel,
                b.sns_join_yn,
                b.email_alarm_yn,
                b.sns_alarm_yn,
                p.name,
                p.nickname,
                p.sex,
                p.phone_no,
                p.address,
                p.email,
                p.sub_email,
                p.profile_image_url
            FROM tb_member_basic_m b
            LEFT JOIN tb_member_profile_t p ON b.member_id = p.member_id
            WHERE b.member_id = %s
            """,
            (member_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Member not found")
        return row
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/nickname/check")
def check_nickname(nickname: str, member_id: Optional[int] = None):
    if not re.fullmatch(r"[A-Za-z0-9가-힣]{2,12}", nickname):
        return {"available": False}

    conn = get_user_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        _ensure_profile_columns(cur)
        if member_id:
            cur.execute(
                "SELECT member_id FROM tb_member_profile_t WHERE nickname=%s AND member_id<>%s",
                (nickname, member_id),
            )
        else:
            cur.execute(
                "SELECT member_id FROM tb_member_profile_t WHERE nickname=%s",
                (nickname,),
            )
        exists = cur.fetchone() is not None
        return {"available": not exists}
    finally:
        cur.close()
        conn.close()


@router.patch("/profile/{member_id}")
def update_profile(member_id: int, req: UpdateProfileRequest):
    conn = get_user_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        _ensure_profile_columns(cur)

        cur.execute(
            "SELECT member_id FROM tb_member_basic_m WHERE member_id=%s",
            (member_id,),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Member not found")

        if req.sex and req.sex not in ("M", "F"):
            raise HTTPException(status_code=400, detail="Invalid sex value")

        if req.sns_join_yn and req.sns_join_yn not in ("Y", "N"):
            raise HTTPException(status_code=400, detail="Invalid sns_join_yn value")

        if req.email_alarm_yn and req.email_alarm_yn not in ("Y", "N"):
            raise HTTPException(status_code=400, detail="Invalid email_alarm_yn value")

        if req.sns_alarm_yn and req.sns_alarm_yn not in ("Y", "N"):
            raise HTTPException(status_code=400, detail="Invalid sns_alarm_yn value")

        nickname = req.nickname
        if nickname is not None:
            if not re.fullmatch(r"[A-Za-z0-9가-힣]{2,12}", nickname):
                raise HTTPException(
                    status_code=400,
                    detail="Nickname must be 2-12 chars (Korean/English/Number) with no symbols",
                )
            cur.execute(
                "SELECT member_id FROM tb_member_profile_t WHERE nickname=%s AND member_id<>%s",
                (nickname, member_id),
            )
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Nickname already exists")

        if req.email is not None:
            cur.execute(
                "SELECT member_id FROM tb_member_basic_m WHERE login_id=%s AND member_id<>%s",
                (req.email, member_id),
            )
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Email already exists")

        cur.execute(
            "SELECT member_id FROM tb_member_profile_t WHERE member_id=%s",
            (member_id,),
        )
        if cur.fetchone():
            cur.execute(
                """
                UPDATE tb_member_profile_t
                SET nickname = COALESCE(%s, nickname),
                    name = COALESCE(%s, name),
                    sex = COALESCE(%s, sex),
                    phone_no = COALESCE(%s, phone_no),
                    address = COALESCE(%s, address),
                    email = COALESCE(%s, email),
                    sub_email = COALESCE(%s, sub_email),
                    profile_image_url = COALESCE(%s, profile_image_url)
                WHERE member_id = %s
                """,
                (
                    req.nickname,
                    req.name,
                    req.sex,
                    req.phone_no,
                    req.address,
                    req.email,
                    req.sub_email,
                    req.profile_image_url,
                    member_id,
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO tb_member_profile_t
                (member_id, nickname, name, sex, phone_no, address, email, sub_email, profile_image_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    member_id,
                    req.nickname,
                    req.name,
                    req.sex,
                    req.phone_no,
                    req.address,
                    req.email,
                    req.sub_email,
                    req.profile_image_url,
                ),
            )

        if req.email is not None:
            cur.execute(
                """
                UPDATE tb_member_basic_m
                SET login_id = %s
                WHERE member_id = %s AND join_channel = 'LOCAL'
                """,
                (req.email, member_id),
            )

        if (
            req.email_alarm_yn in ("Y", "N")
            or req.sns_alarm_yn in ("Y", "N")
            or req.sns_join_yn in ("Y", "N")
        ):
            cur.execute(
                """
                UPDATE tb_member_basic_m
                SET email_alarm_yn = COALESCE(%s, email_alarm_yn),
                    sns_alarm_yn = COALESCE(%s, sns_alarm_yn),
                    sns_join_yn = COALESCE(%s, sns_join_yn)
                WHERE member_id = %s
                """,
                (req.email_alarm_yn, req.sns_alarm_yn, req.sns_join_yn, member_id),
            )

        conn.commit()
        return {"status": "ok"}

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


@router.post("/profile/{member_id}/password")
def update_password(member_id: int, req: UpdatePasswordRequest):
    if req.new_password != req.confirm_password:
        raise HTTPException(
            status_code=400, detail="Password confirmation does not match"
        )

    _validate_password(req.new_password)

    conn = get_user_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute(
            "SELECT member_id FROM tb_member_basic_m WHERE member_id=%s",
            (member_id,),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Member not found")

        cur.execute(
            "SELECT pwd_hash, join_channel FROM tb_member_basic_m WHERE member_id=%s",
            (member_id,),
        )
        row = cur.fetchone()

        if not row or not row.get("pwd_hash"):
            raise HTTPException(status_code=400, detail="Password login not enabled")

        if row.get("join_channel") != "LOCAL":
            raise HTTPException(status_code=400, detail="Password login not enabled")

        if not pwd_context.verify(req.current_password, row["pwd_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        new_hash = pwd_context.hash(req.new_password)
        cur.execute(
            """
            UPDATE tb_member_basic_m
            SET pwd_hash=%s
            WHERE member_id=%s
            """,
            (new_hash, member_id),
        )

        conn.commit()
        return {"status": "ok"}

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


@router.post("/profile/{member_id}/withdraw")
def request_withdraw(member_id: int):
    conn = get_user_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute(
            "SELECT member_id FROM tb_member_basic_m WHERE member_id=%s",
            (member_id,),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Member not found")

        cur.execute(
            """
            INSERT INTO tb_member_status_t (member_id, member_status)
            VALUES (%s, 'WITHDRAW_REQ')
            ON CONFLICT (member_id)
            DO UPDATE SET member_status = EXCLUDED.member_status, alter_dt = CURRENT_TIMESTAMP
            """,
            (member_id,),
        )
        conn.commit()
        return {"status": "ok"}
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


@router.post("/recover")
def recover_account(member_id: int):
    conn = get_user_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute(
            "SELECT member_status FROM tb_member_status_t WHERE member_id=%s",
            (member_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Member not found")

        if row.get("member_status") != "WITHDRAW_REQ":
            raise HTTPException(
                status_code=400, detail="Account is not pending withdrawal"
            )

        cur.execute(
            """
            UPDATE tb_member_status_t
            SET member_status='NORMAL', alter_dt=CURRENT_TIMESTAMP
            WHERE member_id=%s
            """,
            (member_id,),
        )
        conn.commit()
        return {"status": "ok"}
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


@router.post("/profile/{member_id}/image")
def upload_profile_image(member_id: int, file: UploadFile = File(...)):
    if file.content_type not in ("image/png", "image/jpeg", "image/webp", "image/gif"):
        raise HTTPException(status_code=400, detail="Unsupported image type")

    conn = get_user_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        _ensure_profile_columns(cur)
        cur.execute(
            "SELECT member_id FROM tb_member_basic_m WHERE member_id=%s",
            (member_id,),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Member not found")

        cur.execute(
            "SELECT profile_image_url FROM tb_member_profile_t WHERE member_id=%s",
            (member_id,),
        )
        existing = cur.fetchone()

        uploads_dir = os.path.join(os.getcwd(), "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
            ext = ".png"
        filename = f"profile_{member_id}_{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(uploads_dir, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        public_url = f"/uploads/{filename}"

        cur.execute(
            "SELECT member_id FROM tb_member_profile_t WHERE member_id=%s",
            (member_id,),
        )
        if cur.fetchone():
            cur.execute(
                """
                UPDATE tb_member_profile_t
                SET profile_image_url=%s
                WHERE member_id=%s
                """,
                (public_url, member_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO tb_member_profile_t (member_id, profile_image_url)
                VALUES (%s, %s)
                """,
                (member_id, public_url),
            )

        if existing and existing.get("profile_image_url"):
            old_path = existing["profile_image_url"]
            if old_path.startswith("/uploads/"):
                old_file = os.path.join(uploads_dir, os.path.basename(old_path))
                if os.path.exists(old_file):
                    try:
                        os.remove(old_file)
                    except OSError:
                        pass

        conn.commit()
        return {"profile_image_url": public_url}
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


@router.get("/admin/members")
def admin_list_members(admin_member_id: int):
    conn = get_user_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        _ensure_admin_by_member_id(cur, admin_member_id)

        cur.execute(
            """
            SELECT
                b.member_id,
                p.email,
                p.nickname,
                b.join_dt,
                s.member_status,
                b.join_channel
            FROM tb_member_basic_m b
            LEFT JOIN tb_member_profile_t p ON b.member_id = p.member_id
            LEFT JOIN tb_member_status_t s ON b.member_id = s.member_id
            ORDER BY b.member_id DESC
            """
        )
        return {"members": cur.fetchall()}
    finally:
        cur.close()
        conn.close()


@router.patch("/admin/members/{member_id}/status")
def admin_update_member_status(member_id: int, admin_member_id: int, status: str):
    if status not in ("NORMAL", "LOCK", "DORMANT", "WITHDRAW_REQ", "WITHDRAW"):
        raise HTTPException(status_code=400, detail="Invalid status")

    conn = get_user_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        _ensure_admin_by_member_id(cur, admin_member_id)

        cur.execute(
            "SELECT member_id FROM tb_member_basic_m WHERE member_id=%s",
            (member_id,),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Member not found")

        cur.execute(
            """
            INSERT INTO tb_member_status_t (member_id, member_status)
            VALUES (%s, %s)
            ON CONFLICT (member_id)
            DO UPDATE SET member_status = EXCLUDED.member_status
            """,
            (member_id, status),
        )
        conn.commit()
        return {"status": "ok"}
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


class SavePerfumeRequest(BaseModel):
    member_id: int  # 로그인된 사용자 ID (프론트에서 세션 정보로 보냄)
    perfume_id: int
    perfume_name: str


@router.post("/me/perfumes")
def save_my_perfume(req: SavePerfumeRequest):
    """
    사용자가 '저장하기' 버튼을 눌렀을 때 호출되는 API입니다.
    TB_MEMBER_MY_PERFUME_T 테이블에 향수를 저장합니다.
    """
    if not req.member_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    # DB 저장 함수 호출
    result = add_my_perfume(req.member_id, req.perfume_id, req.perfume_name)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    # 이미 저장된 경우도 성공(200)으로 처리하되 메시지만 다르게 줄 수 있음
    return result
