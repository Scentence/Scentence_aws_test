import json
import psycopg2
import psycopg2.extras
from typing import List, Dict, Any, Optional

# 기존 DB 연결 풀은 재사용 (연결 설정은 공용이므로 안전)
from .database import get_db_connection, release_db_connection

def get_my_perfumes(member_id: int) -> List[Dict[str, Any]]:
    """
    [아카이브] 사용자가 등록한 향수 목록 조회 (최신순)
    """
    conn = get_db_connection()
    if not conn:
        print("DB Connection Failed")
        return []
    
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # 1. 사용자가 등록(HAVE)했거나 추천받은(RECOMMENDED) 향수 목록 조회
        # (테이블 구조에 따라 로직 조정 가능, 여기서는 HAVE/RECOMMENDED 모두 조회)
        query = """
            SELECT 
                mp.my_perfume_id,
                mp.member_id,
                mp.perfume_id,
                mp.register_status,
                mp.register_dt,
                p.name as perfume_name,
                p.brand as perfume_brand,
                p.image_url as perfume_image
            FROM tb_my_perfume_m mp
            JOIN tb_perfume_m p ON mp.perfume_id = p.perfume_id
            WHERE mp.member_id = %s
            ORDER BY mp.register_dt DESC
        """
        cur.execute(query, (member_id,))
        rows = cur.fetchall()
        
        # 날짜 객체 문자열 변환 등 전처리
        result = []
        for row in rows:
            row_dict = dict(row)
            if row_dict.get('register_dt'):
                row_dict['register_dt'] = str(row_dict['register_dt'])
            result.append(row_dict)
            
        return result
        
    except Exception as e:
        print(f"Error getting my perfumes: {e}")
        return []
    finally:
        cur.close()
        release_db_connection(conn)

def add_my_perfume(member_id: int, perfume_id: int, status: str = 'HAVE'):
    """
    [아카이브] 내 향수 등록 (기존 함수 대체)
    """
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "DB Connection Failed"}
        
    cur = conn.cursor()
    try:
        # 중복 체크
        check_sql = "SELECT my_perfume_id FROM tb_my_perfume_m WHERE member_id = %s AND perfume_id = %s"
        cur.execute(check_sql, (member_id, perfume_id))
        if cur.fetchone():
            return {"status": "error", "message": "Already registered"}
            
        insert_sql = """
            INSERT INTO tb_my_perfume_m (member_id, perfume_id, register_status, register_dt)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
        """
        cur.execute(insert_sql, (member_id, perfume_id, status))
        conn.commit()
        return {"status": "success"}
        
    except Exception as e:
        conn.rollback()
        print(f"Error adding my perfume: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        cur.close()
        release_db_connection(conn)

def delete_my_perfume(member_id: int, perfume_id: int):
    """
    [아카이브] 내 향수 삭제
    """
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "DB Connection Failed"}
        
    cur = conn.cursor()
    try:
        delete_sql = "DELETE FROM tb_my_perfume_m WHERE member_id = %s AND perfume_id = %s"
        cur.execute(delete_sql, (member_id, perfume_id))
        conn.commit()
        return {"status": "success"}
        
    except Exception as e:
        conn.rollback()
        print(f"Error deleting my perfume: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        cur.close()
        release_db_connection(conn)
