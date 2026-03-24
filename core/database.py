import os
import psycopg2
from dotenv import load_dotenv
load_dotenv()

# Connect to the database
def get_connection():
    """Creates and returns a Supabase PostgreSQL connection."""
    DATABASE_URL = os.getenv("SUPABASE_DB_URL")
    if not DATABASE_URL:
        raise ValueError("SUPABASE_DB_URL not found in environment variables.")
    return psycopg2.connect(DATABASE_URL)

def init_db():
    """Ensures the evaluated_jobs table exists. Returns connection."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluated_jobs (
            url TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            ai_score INTEGER,
            ai_reasoning TEXT,
            date_discovered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            email_sent BOOLEAN DEFAULT FALSE
        )
    """)
    conn.commit()
    cursor.close()
    return conn

def is_job_evaluated(conn, url: str) -> bool:
    """Returns True if this URL already exists in the database."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT url FROM evaluated_jobs WHERE url = %s",
        (url,)
    )
    result = cursor.fetchone()
    cursor.close()
    return result is not None

def save_evaluation(conn, job: dict, score: float, reasoning: str):
    """Saves a job evaluation result to Supabase."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO evaluated_jobs (url, title, company, ai_score, ai_reasoning)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (url) DO NOTHING
    """, (
        job['link'],
        job['title'],
        job['company'],
        int(round(score)),
        reasoning
    ))
    conn.commit()


def mark_jobs_as_sent(conn, urls: list):
    """Marks a list of job URLs as emailed so they are never sent again."""
    if not urls:
        return
    cursor = conn.cursor()
    cursor.executemany(
        "UPDATE evaluated_jobs SET email_sent = TRUE WHERE url = %s",
        [(url,) for url in urls]
    )
    conn.commit()
    cursor.close()