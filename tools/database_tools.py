
import psycopg2
from dotenv import load_dotenv
import os

def connect():
    # Update cards table in database
    load_dotenv()
    conn = psycopg2.connect(
        dbname=os.getenv("PG_NAME"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        host=os.getenv("PG_HOST", "localhost"),
        port=os.getenv("PG_PORT", "5432")
    )
    cur = conn.cursor()
    print("Connected to PostgreSQL")
    return conn, cur

conn, cur = connect()

__all__ = ["conn", "cur"]