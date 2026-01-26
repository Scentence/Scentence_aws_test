import os
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
from dotenv import load_dotenv
import logging

load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 환경변수 로드
DATABASE_URL = os.getenv("PERFUME_DATABASE_URL", "")
RECOM_DATABASE_URL = os.getenv("RECOM_DATABASE_URL", "")

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "perfume_db"),
    "user": os.getenv("DB_USER", "scentence"),
    "password": os.getenv("DB_PASSWORD", "scentence"),
    "host": os.getenv("DB_HOST", "host.docker.internal"),
    "port": os.getenv("DB_PORT", "5435"),
}

_pg_pool = None
_recom_pg_pool = None


def initialize_pool():
    global _pg_pool
    try:
        if not _pg_pool:
            if DATABASE_URL:
                logger.info(f"🔌 Connecting via PERFUME_DATABASE_URL...")
                _pg_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=1, maxconn=10, dsn=DATABASE_URL
                )
            else:
                logger.info(f"🔌 Connecting via DB_CONFIG...")
                _pg_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=1, maxconn=10, **DB_CONFIG
                )
            logger.info("✅ DB Connection Pool created successfully")
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f"❌ Error while connecting to PostgreSQL: {error}")


def initialize_recom_pool():
    global _recom_pg_pool
    try:
        if not _recom_pg_pool:
            if RECOM_DATABASE_URL:
                logger.info("🔌 Connecting via RECOM_DATABASE_URL...")
                _recom_pg_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=1, maxconn=10, dsn=RECOM_DATABASE_URL
                )
            else:
                recom_db_config = {
                    "dbname": os.getenv("RECOM_DB_NAME", "recom_db"),
                    "user": os.getenv("RECOM_DB_USER", DB_CONFIG["user"]),
                    "password": os.getenv("RECOM_DB_PASSWORD", DB_CONFIG["password"]),
                    "host": os.getenv("RECOM_DB_HOST", DB_CONFIG["host"]),
                    "port": os.getenv("RECOM_DB_PORT", DB_CONFIG["port"]),
                }
                logger.info("🔌 Connecting via RECOM_DB_CONFIG...")
                _recom_pg_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=1, maxconn=10, **recom_db_config
                )
            logger.info("✅ Recom DB Connection Pool created successfully")
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f"❌ Error while connecting to Recom DB: {error}")


def close_pool():
    global _pg_pool
    if _pg_pool:
        _pg_pool.closeall()
        logger.info("🛑 DB Connection Pool closed")


def close_recom_pool():
    global _recom_pg_pool
    if _recom_pg_pool:
        _recom_pg_pool.closeall()
        logger.info("🛑 Recom DB Connection Pool closed")


@contextmanager
def get_db_connection():
    global _pg_pool
    if not _pg_pool:
        initialize_pool()
    conn = _pg_pool.getconn()
    try:
        yield conn
    finally:
        _pg_pool.putconn(conn)


@contextmanager
def get_recom_db_connection():
    global _recom_pg_pool
    if not _recom_pg_pool:
        initialize_recom_pool()
    conn = _recom_pg_pool.getconn()
    try:
        yield conn
    finally:
        _recom_pg_pool.putconn(conn)


# [추가됨] 테이블 자동 생성 함수
def init_db_schema():
    """
    서버 시작 시 또는 배치 시작 시 호출되어
    필요한 테이블이 없으면 자동으로 생성합니다.
    """
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS TB_PERFUME_SIMILARITY (
        perfume_id_a INTEGER NOT NULL,
        perfume_id_b INTEGER NOT NULL,
        score FLOAT NOT NULL,
        PRIMARY KEY (perfume_id_a, perfume_id_b)
    );
    
    -- 기존 인덱스
    CREATE INDEX IF NOT EXISTS idx_sim_score ON TB_PERFUME_SIMILARITY (score DESC);
    CREATE INDEX IF NOT EXISTS idx_sim_a ON TB_PERFUME_SIMILARITY (perfume_id_a);
    
    -- 성능 최적화 인덱스 (유사도 엣지 조회 속도 향상)
    CREATE INDEX IF NOT EXISTS idx_sim_b ON TB_PERFUME_SIMILARITY (perfume_id_b);
    CREATE INDEX IF NOT EXISTS idx_sim_score_a ON TB_PERFUME_SIMILARITY (score DESC, perfume_id_a);
    CREATE INDEX IF NOT EXISTS idx_sim_score_b ON TB_PERFUME_SIMILARITY (score DESC, perfume_id_b);
    """

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_table_sql)
                conn.commit()
        logger.info("✅ Database schema initialized (Table check complete).")
    except Exception as e:
        logger.error(f"❌ Failed to initialize DB schema: {e}")
