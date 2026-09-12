import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
print("✅ Connected to Supabase PostgreSQL!")

conn.close()