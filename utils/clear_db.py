import sqlite3
import os

def truncate_database():
    """Clears all records from the evaluated_jobs table and reclaims disk space."""
    # Navigate up to the root, then down into the data folder
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "data", "jobs_state.db")
    
    print(f"[*] Accessing database at: {db_path}")
    
    if not os.path.exists(db_path):
        print("[-] Error: Database file not found in data/. Nothing to truncate.")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Delete all rows (The SQLite version of TRUNCATE)
        print("[*] Wiping all records from 'evaluated_jobs' table...")
        cursor.execute("DELETE FROM evaluated_jobs")
        
        # THE SENIOR FIX: Commit the delete transaction BEFORE vacuuming
        conn.commit()
        
        # 2. VACUUM to defragment the database and free up disk space
        print("[*] Vacuuming database to reclaim disk space...")
        cursor.execute("VACUUM")
        
        print("[+] SUCCESS: Database truncated! The table is empty, but the schema is ready for new data.")
        
    except sqlite3.Error as e:
        print(f"[-] SQLite Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("\n" + "="*50)
    print(" ⚠️  DATABASE TRUNCATION PROTOCOL ⚠️")
    print("="*50)
    confirm = input("Are you absolutely sure you want to wipe the AI's memory? (y/n): ")
    
    if confirm.lower() == 'y':
        truncate_database()
    else:
        print("[*] Aborted. Your data is safe.")