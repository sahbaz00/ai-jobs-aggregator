import sqlite3
import os
import pandas as pd

def inspect_and_export():
    """Pulls raw data, prints a clean summary to the terminal, and exports everything to Excel."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "data", "jobs_state.db")
    excel_path = os.path.join(base_dir, "data", "jobs_database_dump.xlsx")
    
    print(f"[*] Accessing database at: {db_path}\n")
    
    if not os.path.exists(db_path):
        print("[-] Error: jobs_state.db does not exist. Run agent.py first.")
        return

    try:
        conn = sqlite3.connect(db_path)
        
        # Pull EVERYTHING for the Excel file
        query = "SELECT title, company, ai_score, ai_reasoning, url, date_discovered FROM evaluated_jobs"
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            print("[-] The database is connected, but the table is empty.")
        else:
            print(f"[+] Found {len(df)} records in the database.\n")
            
            # 1. THE TERMINAL VIEW (Clean & Readable)
            # We hide the long URLs and dates just for the terminal output
            terminal_df = df[['title', 'company', 'ai_score', 'ai_reasoning']]
            pd.set_option('display.max_rows', None)
            pd.set_option('display.max_colwidth', 80)
            print("--- TERMINAL PREVIEW ---")
            print(terminal_df)
            print("-" * 24)
            
            # 2. THE EXCEL EXPORT (Comprehensive)
            print(f"\n[*] Exporting full database to Excel...")
            # We use openpyxl as the engine to write the .xlsx file
            df.to_excel(excel_path, index=False, engine='openpyxl')
            print(f"[+] SUCCESS: Full database exported to {excel_path}")
            print(f"    -> You can open this file in Microsoft Excel or Google Sheets.")
            
    except sqlite3.Error as e:
        print(f"[-] SQLite Error: {e}")
    except ModuleNotFoundError:
        print("[-] Missing Dependency: Please run 'pip install openpyxl' in your terminal to enable Excel exports.")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    inspect_and_export()