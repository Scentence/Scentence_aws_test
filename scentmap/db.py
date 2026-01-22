import os

import psycopg2
from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("PERFUME_DATABASE_URL", "")

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "perfume_db"),
    "user": os.getenv("DB_USER", "scentence"),
    "password": os.getenv("DB_PASSWORD", "scentence"),
    "host": os.getenv("DB_HOST", "host.docker.internal"),
    "port": os.getenv("DB_PORT", "5435"),
}

def get_db_connection():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    return psycopg2.connect(**DB_CONFIG)
