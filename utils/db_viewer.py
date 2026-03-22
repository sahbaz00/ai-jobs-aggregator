import sqlite3
import datetime
import os

def export_to_markdown(min_score=0):
    """Queries the SQLite database and generates a clean Markdown report."""
    
    # THE SENIOR FIX: Absolute Pathing
    # This forces Python to look in the exact folder where this script lives
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "data", "jobs_state.db")
    
    print(f"[*] Accessing local database at: {db_path}")
    
    if not os.path.exists(db_path):
        print("[-] Error: jobs_state.db file does not exist in this folder. Run agent.py first.")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT title, company, ai_score, ai_reasoning, url, date_discovered 
            FROM evaluated_jobs 
            WHERE ai_score >= ?
            ORDER BY ai_score DESC, date_discovered DESC
        ''', (min_score,))
        
        jobs = cursor.fetchall()
        
    except sqlite3.OperationalError as e:
        # If it fails now, it will tell us the EXACT reason why
        print(f"[-] SQLite Error: {e}")
        print("    -> Tip: Is the database open or locked by a VS Code extension?")
        return

    if not jobs:
        print(f"[-] No jobs found matching the minimum score of {min_score}.")
        return

    filename = os.path.join(base_dir, "data", "Top_Job_Matches.md")
    print(f"[*] Generating Top_Job_Matches.md...")
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# 🚀 AI Job Aggregator Results\n")
        f.write(f"*Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        f.write(f"Total evaluated jobs found: **{len(jobs)}**\n\n")
        f.write("---\n\n")
        
        for job in jobs:
            title, company, score, reasoning, link, date = job
            
            if score >= 85:
                badge = "🟢" 
            elif score >= 60:
                badge = "🟡"
            else:
                badge = "🔴"
                
            f.write(f"### {badge} [{score}/100] {title} @ {company}\n")
            f.write(f"- **AI Verdict:** {reasoning}\n")
            f.write(f"- **Apply Here:** [Link to Application]({link})\n")
            f.write(f"- *Discovered:* {date.split(' ')[0]}\n\n")
            f.write("---\n\n")
            
    print(f"[+] SUCCESS: Exported {len(jobs)} jobs to Top_Job_Matches.md")
    print(f"    -> Open the file in VS Code and click the 'Preview' button to view it!")

if __name__ == "__main__":
    export_to_markdown(min_score=0)