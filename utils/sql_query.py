import os
import psycopg2
from dotenv import load_dotenv
load_dotenv()

def get_connection():
    """Creates and returns a Supabase PostgreSQL connection."""
    DATABASE_URL = os.getenv("SUPABASE_DB_URL")
    if not DATABASE_URL:
        raise ValueError("SUPABASE_DB_URL not found in environment variables.")
    return psycopg2.connect(DATABASE_URL)

conn = get_connection()

cursor = conn.cursor()
# cursor.execute(
#     """SELECT url, title, count(*) as count 
#     FROM evaluated_jobs 
#     GROUP BY url, title 
#     HAVING count(*) > 1;"""
# )

# cursor.execute(
#     """
#     SELECT url, title
#     FROM evaluated_jobs;
#     """
# )

# check RLS (Row Level Security) activated or not
cursor.execute(
    """
    SELECT tablename, rowsecurity 
    FROM pg_tables
    WHERE tablename = 'evaluated_jobs';
    """
)

result = cursor.fetchall()
print(result)