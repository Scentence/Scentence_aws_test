import os
import subprocess
import sys
import time

# ==========================================
# 설정
# ==========================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 실행할 스크립트 목록 (순서대로 실행됨)
# 1. load_note_vectors.py: 노트 임베딩 (raw 폴더 사용)
# 2. load_review_vectors.py: 리뷰 임베딩 (review_split 폴더 사용)
ETL_SCRIPTS = ["load_note_vectors.py", "load_review_vectors.py"]


def run_etl_pipeline():
    print("=================================================")
    print("🚀 [Vector ETL] 벡터 DB 적재 파이프라인 시작")
    print(f"📂 작업 경로: {CURRENT_DIR}")
    print(f"📋 실행 목록: {ETL_SCRIPTS}")
    print("=================================================\n")

    total_start_time = time.time()

    for i, script_name in enumerate(ETL_SCRIPTS, 1):
        script_path = os.path.join(CURRENT_DIR, script_name)

        print(f"▶️ [Step {i}/{len(ETL_SCRIPTS)}] {script_name} 실행 중...")

        # 파일 존재 확인
        if not os.path.exists(script_path):
            print(f"❌ 오류: 스크립트 파일이 없습니다 -> {script_path}")
            sys.exit(1)

        # 서브프로세스로 파이썬 스크립트 실행
        # check=True: 에러 발생 시 즉시 예외 발생시켜 중단
        try:
            start_time = time.time()

            # python -u (unbuffered): 로그 즉시 출력
            subprocess.run(["python", "-u", script_path], check=True)

            elapsed = time.time() - start_time
            print(f"✅ [Step {i}] 완료 ({elapsed:.2f}초)\n")

        except subprocess.CalledProcessError as e:
            print(f"\n❌ [Critical] ETL 실행 중단: {script_name} 에서 에러 발생")
            print(f"   Exit Code: {e.returncode}")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ [Critical] 알 수 없는 오류: {e}")
            sys.exit(1)

    total_elapsed = time.time() - total_start_time
    print("=================================================")
    print(f"🎉 모든 벡터 ETL 작업이 성공적으로 끝났습니다!")
    print(f"⏱️ 총 소요 시간: {total_elapsed:.2f}초")
    print("=================================================")


if __name__ == "__main__":
    # 도커 로그 즉시 출력을 위해 stdout 플러시
    sys.stdout.reconfigure(line_buffering=True)
    run_etl_pipeline()
