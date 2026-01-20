import os

import psycopg2
from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("PERFUME_DATABASE_URL", "")
DB_CONFIG = {
    "dbname": os.getenv("PERFUME_DB_NAME", "perfume_db"),
    "user": os.getenv("PERFUME_DB_USER", "scentence"),
    "password": os.getenv("PERFUME_DB_PASSWORD", "scentence"),
    "host": os.getenv("PERFUME_DB_HOST", os.getenv("DB_HOST", "localhost")),
    "port": os.getenv("PERFUME_DB_PORT", os.getenv("DB_PORT", "5433")),
}


def get_db_connection():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    return psycopg2.connect(**DB_CONFIG)