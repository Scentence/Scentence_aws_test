import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# [재검증] scentence_db가 아니라 무조건 member_db 명시
# 로그에 따르면 현재 'scentence_db' 등으로 잘못 접속 중일 가능성 높음
USER_DB_PARAMS = {
    "dbname": "member_db", 
    "user": "scentence",
    "password": "scentence",
    "host": "db",  # docker-compose 서비스명
    "port": "5432"
}

def get_user_db_connection():
    return psycopg2.connect(**USER_DB_PARAMS)