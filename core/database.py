import sqlite3

def init_db(db_name="data/jobs_state.db"):
    """Initializes the local SQLite database and creates the state table."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # We use the URL as the PRIMARY KEY. This guarantees no duplicates.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS evaluated_jobs (
            url TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            ai_score INTEGER,
            ai_reasoning TEXT,
            date_discovered TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

def is_job_evaluated(conn, url):
    """Checks if a job URL already exists in the database."""
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM evaluated_jobs WHERE url = ?', (url,))
    return cursor.fetchone() is not None

def save_evaluation(conn, job, score, reasoning):
    """Saves the AI's evaluation to the database so we never process it again."""
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO evaluated_jobs (url, title, company, ai_score, ai_reasoning)
        VALUES (?, ?, ?, ?, ?)
    ''', (job['link'], job['title'], job['company'], score, reasoning))
    conn.commit()