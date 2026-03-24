import psycopg2
import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path=dotenv_path)

def truncate_database():
    """Clears all records from evaluated_jobs in Supabase without dropping the table."""

    database_url = os.getenv("SUPABASE_DB_URL")
    if not database_url:
        print("[-] Error: SUPABASE_DB_URL not found in .env file.")
        return

    print("[*] Connecting to Supabase...")

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        print("[*] Wiping all records from 'evaluated_jobs' table...")

        # PostgreSQL has native TRUNCATE — faster than DELETE for full wipes
        # RESTART IDENTITY resets any auto-increment counters (good practice)
        cursor.execute("TRUNCATE TABLE evaluated_jobs RESTART IDENTITY;")
        conn.commit()

        # No VACUUM needed — PostgreSQL handles this automatically
        # unlike SQLite which requires manual VACUUM

        print("[+] SUCCESS: Table truncated. Schema intact, data cleared.")
        cursor.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"[-] PostgreSQL Error: {e}")

if __name__ == "__main__":
    print("\n" + "="*50)
    print(" ⚠️  DATABASE TRUNCATION PROTOCOL ⚠️")
    print("="*50)
    confirm = input("Are you absolutely sure you want to wipe the AI's memory? (y/n): ")

    if confirm.lower() == 'y':
        truncate_database()
    else:
        print("[*] Aborted. Your data is safe.")