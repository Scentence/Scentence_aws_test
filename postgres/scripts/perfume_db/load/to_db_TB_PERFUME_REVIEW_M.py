import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
import os
import numpy as np

# 경로 확인 필수
CSV_PATH = "outputs/TB_PERFUME_REVIEW_M.tsv"
TABLE_NAME = "TB_PERFUME_REVIEW_M"
BATCH_SIZE = 1000

DB_CONFIG = {
    "dbname": "perfume_db",
    "user": "scentence",
    "password": "scentence",
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5433"),
}


def get_valid_perfume_ids(conn):
    """DB의 향수 마스터 테이블에서 존재하는 모든 ID를 가져옴"""
    with conn.cursor() as cur:
        print("🔍 유효한 PERFUME_ID 목록을 조회 중...")
        # 마스터 테이블 이름이 TB_PERFUME_BASIC_M 이라고 가정
        cur.execute("SELECT PERFUME_ID FROM TB_PERFUME_BASIC_M")
        # 검색 속도를 위해 set으로 변환
        valid_ids = set(row[0] for row in cur.fetchall())
        print(f"   -> 총 {len(valid_ids)}개의 유효한 향수 ID 확인됨.")
        return valid_ids


def load_data():
    print(f"📂 데이터 로딩 시작: {CSV_PATH}")

    try:
        df = pd.read_csv(CSV_PATH, sep="\t")
    except FileNotFoundError:
        print(f"[SKIP] 파일이 없습니다: {CSV_PATH}")
        return

    if df.empty:
        print(f"[SKIP] 데이터가 비어있습니다.")
        return

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)

        # 1. [핵심] 유효한 향수 ID 목록 가져오기
        valid_ids = get_valid_perfume_ids(conn)

        # 2. 데이터 필터링 (없는 향수 ID 제거)
        original_count = len(df)

        # isin()을 사용하여 존재하는 ID만 남김
        df = df[df["PERFUME_ID"].isin(valid_ids)].copy()

        filtered_count = len(df)
        dropped_count = original_count - filtered_count

        if dropped_count > 0:
            print(
                f"⚠️ [WARNING] {dropped_count}개의 리뷰가 '없는 향수 ID'여서 제외되었습니다."
            )
            print(f"   (남은 데이터: {filtered_count}건)")

        if df.empty:
            print("❌ 적재할 유효한 데이터가 없습니다.")
            return

        # 3. NaN 처리 및 변환
        df = df.replace({np.nan: None})
        records = df.to_dict(orient="records")

        # 4. 적재 쿼리
        insert_sql = f"""
            INSERT INTO {TABLE_NAME} (
                REVIEW_ID,
                PERFUME_ID,
                CONTENT,
                TAGS,
                SOURCE,
                LOAD_DT
            )
            VALUES (
                %(REVIEW_ID)s,
                %(PERFUME_ID)s,
                %(CONTENT)s,
                %(TAGS)s,
                %(SOURCE)s,
                %(LOAD_DT)s
            )
            ON CONFLICT (REVIEW_ID)
            DO UPDATE SET
                CONTENT = EXCLUDED.CONTENT,
                TAGS = EXCLUDED.TAGS,
                SOURCE = EXCLUDED.SOURCE,
                LOAD_DT = EXCLUDED.LOAD_DT
        """

        with conn:
            with conn.cursor() as cur:
                print(f"🚀 {len(records)}건의 데이터 적재(Upsert)를 시작합니다...")
                execute_batch(cur, insert_sql, records, page_size=BATCH_SIZE)

        print(f"[OK] {TABLE_NAME} 적재 완료! (총 {len(records)}건)")

    except Exception as e:
        print(f"[FAIL] 적재 중 오류 발생: {e}")
        raise

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    load_data()
