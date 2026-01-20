import pandas as pd
import os
import glob
from datetime import datetime

# === 설정 ===
INPUT_DIR = "raw/reviews"  # 원본 파일 경로
OUTPUT_DIR = "outputs"  # 저장 경로
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "TB_PERFUME_REVIEW_M.tsv")


def clean_text_column(series):
    """
    Pandas Series(컬럼)을 받아서
    1. 결측치(NaN)는 빈 문자열로 채우고
    2. 탭(\t), 줄바꿈(\n), 캐리지리턴(\r)을 공백(' ')으로 치환
    """
    return (
        series.fillna("")  # NaN -> ""
        .astype(str)  # 문자열 변환
        .str.replace(r"[\t\r\n]+", " ", regex=True)  # 특수문자 -> 공백 치환
        .str.strip()  # 양끝 불필요한 공백 제거
    )


def merge_and_clean():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    tsv_files = glob.glob(os.path.join(INPUT_DIR, "*.tsv"))

    if not tsv_files:
        print("❌ 처리할 TSV 파일이 없습니다.")
        return

    merged_list = []
    print(f"🧹 데이터 정제 및 병합 시작 (대상 파일: {len(tsv_files)}개)...")

    for file_path in tsv_files:
        filename = os.path.basename(file_path)
        print(f"   Reading & Cleaning {filename}...")

        # 1. 파일 읽기
        df = pd.read_csv(file_path, sep="\t")

        # 2. SOURCE 컬럼 추가
        if "fragrantica" in filename.lower():
            df["SOURCE"] = "Fragrantica"
        elif "parfumo" in filename.lower():
            df["SOURCE"] = "Parfumo"
        else:
            df["SOURCE"] = "Unknown"

        # 3. ID 전처리 (R_, P_ 제거 -> 숫자 변환)
        df["REVIEW_ID"] = (
            df["review_id"].astype(str).str.replace("R_", "", regex=False).astype(int)
        )
        df["PERFUME_ID"] = (
            df["perfume_id"].astype(str).str.replace("P_", "", regex=False).astype(int)
        )

        # 4. 컬럼명 통일 (content -> CONTENT, tags -> TAGS)
        df.rename(columns={"content": "CONTENT", "tags": "TAGS"}, inplace=True)
        if "TAGS" not in df.columns:
            df["TAGS"] = ""

        # ==========================================================
        # ★ 5. 핵심: 특수문자(탭, 줄바꿈) 제거 (Data Cleaning) ★
        # ==========================================================
        print(f"     -> 특수문자(\\t, \\n) 제거 중...")
        df["CONTENT"] = clean_text_column(df["CONTENT"])
        df["TAGS"] = clean_text_column(df["TAGS"])

        merged_list.append(df)

    # 6. 병합 및 저장
    if merged_list:
        final_df = pd.concat(merged_list, ignore_index=True)

        # 로드 시간 추가
        final_df["LOAD_DT"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 최종 컬럼 순서
        target_columns = [
            "REVIEW_ID",
            "PERFUME_ID",
            "CONTENT",
            "TAGS",
            "SOURCE",
            "LOAD_DT",
        ]
        final_df = final_df[target_columns]

        # TSV 저장
        # index=False: 인덱스 번호 제외
        # sep='\t': 탭으로 구분
        # encoding='utf-8-sig': 한글 깨짐 방지
        final_df.to_csv(OUTPUT_FILE, sep="\t", index=False, encoding="utf-8-sig")
        print(f"   -> 총 데이터: {len(final_df)}행")

    else:
        print("❌ 데이터가 없습니다.")


if __name__ == "__main__":
    merge_and_clean()
