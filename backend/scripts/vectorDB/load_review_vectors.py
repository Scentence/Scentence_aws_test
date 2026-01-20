import os
import json
import glob
import re
import psycopg2
from psycopg2.extras import execute_batch

# ==========================================
# 1. 설정
# ==========================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# 데이터 폴더: backend/scripts/vectorDB/review_split
DATA_DIR = os.path.join(CURRENT_DIR, "review_split")
SEARCH_PATTERN = os.path.join(DATA_DIR, "*.json")

DB_CONFIG = {
    "dbname": "perfume_db",
    "user": "scentence",
    "password": "scentence",
    "host": os.getenv("DB_HOST", "db"),
    "port": os.getenv("DB_PORT", "5432"),
}

TABLE_NAME = "tb_review_embedding_m"
REF_TABLE_NAME = "tb_perfume_review_m"


def clean_id(id_val):
    """'R_139300' -> 139300 (숫자만 추출)"""
    if isinstance(id_val, int):
        return id_val
    try:
        nums = re.sub(r"[^0-9]", "", str(id_val))
        return int(nums) if nums else None
    except:
        return None


def load_review_vectors():
    print(f"🚀 [Review-Vector] 리뷰 임베딩 적재 시작")
    print(f"📂 데이터 경로: {DATA_DIR}")

    json_files = sorted(glob.glob(SEARCH_PATTERN))
    if not json_files:
        print(f"❌ '{DATA_DIR}' 안에 JSON 파일이 없습니다.")
        return

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # 2. 테이블 생성 (벡터 확장 포함)
        print("🛠️ 테이블 생성 및 초기화 중...")
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                review_id BIGINT PRIMARY KEY,
                embedding vector(1536),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_review_meta
                    FOREIGN KEY (review_id)
                    REFERENCES {REF_TABLE_NAME} (review_id)
                    ON DELETE CASCADE
            );
        """
        cur.execute(create_sql)
        conn.commit()

        # 3. 파일 순회 및 적재
        total_inserted = 0

        for file_path in json_files:
            filename = os.path.basename(file_path)
            print(f"\n📄 Reading {filename}...")

            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except:
                    print(f"   ❌ JSON 파싱 오류. Skip.")
                    continue

            if not data:
                continue

            records = []

            for item in data:
                # 1. ID 추출 (review_id)
                raw_id = item.get("review_id")

                # 2. [핵심 수정] 벡터 추출 (semantic_vector 사용!)
                vector = item.get("semantic_vector")

                # 만약 semantic_vector가 없으면 혹시 모르니 embedding도 찾아봄 (안전장치)
                if vector is None:
                    vector = item.get("embedding")

                if raw_id is None or vector is None:
                    continue

                # 3. ID 정제 (R_ 제거)
                clean_review_id = clean_id(raw_id)

                if clean_review_id:
                    records.append((clean_review_id, vector))

            # 배치 적재
            if records:
                insert_sql = f"""
                    INSERT INTO {TABLE_NAME} (review_id, embedding)
                    VALUES (%s, %s)
                    ON CONFLICT (review_id) 
                    DO UPDATE SET embedding = EXCLUDED.embedding;
                """
                try:
                    execute_batch(cur, insert_sql, records, page_size=1000)
                    conn.commit()
                    total_inserted += len(records)
                    print(f"   ✅ {len(records)}건 적재 완료")
                except psycopg2.IntegrityError:
                    conn.rollback()
                    print(
                        f"   ⚠️ [Skip] 외래키 오류 (메타 테이블에 ID 없음). 이 배치는 건너뜁니다."
                    )
            else:
                print(
                    "   -> ❌ 유효한 데이터 없음 (review_id 또는 semantic_vector 누락)"
                )

        print(f"\n🎉 작업 완료! 총 {total_inserted}개의 리뷰 벡터가 저장되었습니다.")

        # 최종 확인
        cur.execute(f"SELECT count(*) FROM {TABLE_NAME};")
        cnt = cur.fetchone()[0]
        print(f"📊 현재 DB 저장된 총 개수: {cnt}개")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    load_review_vectors()
