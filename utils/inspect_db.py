import pandas as pd
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path=dotenv_path)

def inspect_and_export():
    """Pulls raw data from Supabase, prints terminal summary, exports to Excel."""

    database_url = os.getenv("SUPABASE_DB_URL")
    if not database_url:
        print("[-] Error: SUPABASE_DB_URL not found in .env file.")
        return
    
    # SENIOR DEV TRICK: SQLAlchemy strictly requires 'postgresql://' not 'postgres://'
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    excel_path = os.path.join(base_dir, "data", "jobs_database_dump.xlsx")

    print("[*] Connecting to Supabase via SQLAlchemy...\n")

    try:
        # Create the SQLAlchemy Engine (This replaces the raw psycopg2 connection)
        engine = create_engine(database_url)

        query = "SELECT title, company, ai_score, ai_reasoning, url, date_discovered FROM evaluated_jobs ORDER BY ai_score DESC"
        
        # Pandas loves SQLAlchemy engines. No more warnings!
        df = pd.read_sql_query(query, engine)

        if df.empty:
            print("[-] Connected successfully, but the table is empty.")
            return

        print(f"[+] Found {len(df)} records in Supabase.\n")

        terminal_df = df[['title', 'company', 'ai_score', 'ai_reasoning']]
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_colwidth', 80)
        print("--- TERMINAL PREVIEW ---")
        print(terminal_df)
        print("-" * 24)

        print(f"\n[*] Exporting full database to Excel...")
        df.to_excel(excel_path, index=False, engine='openpyxl')
        print(f"[+] SUCCESS: Exported to {excel_path}")
        print("    -> Open in Microsoft Excel or Google Sheets.")

    except Exception as e:
        print(f"[-] Database Error: {e}")
    except ModuleNotFoundError:
        print("[-] Missing dependency: run 'uv add openpyxl' to enable Excel export.")

if __name__ == "__main__":
    inspect_and_export()