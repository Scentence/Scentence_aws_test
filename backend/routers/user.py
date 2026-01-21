import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# [수정] 모든 설정을 환경 변수에서 읽어오되, 기본값을 설정합니다.
USER_DB_PARAMS = {
    "dbname": "member_db",  # 회원 전용 DB 명시
    "user": os.getenv("DB_USER", "scentence"),
    "password": os.getenv("DB_PASSWORD", "scentence"),
    # 도커 내부에서 로컬 DB에 접속하기 위해 host.docker.internal 사용
    "host": os.getenv("DB_HOST", "host.docker.internal"),
    "port": os.getenv("DB_PORT", "5432"),
}


def get_user_db_connection():
    return psycopg2.connect(**USER_DB_PARAMS)
