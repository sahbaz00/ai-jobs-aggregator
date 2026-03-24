import psycopg2
import datetime
import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path=dotenv_path)

def export_to_markdown(min_score=0):
    """Queries Supabase and generates a clean Markdown report."""

    database_url = os.getenv("SUPABASE_DB_URL")
    if not database_url:
        print("[-] Error: SUPABASE_DB_URL not found in .env file.")
        return

    print("[*] Connecting to Supabase...")

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT title, company, ai_score, ai_reasoning, url, date_discovered
            FROM evaluated_jobs
            WHERE ai_score >= %s
            ORDER BY ai_score DESC, date_discovered DESC
        ''', (min_score,))

        jobs = cursor.fetchall()
        cursor.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"[-] PostgreSQL Error: {e}")
        return

    if not jobs:
        print(f"[-] No jobs found with minimum score of {min_score}.")
        return

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filename = os.path.join(base_dir, "data", "Top_Job_Matches.md")
    print("[*] Generating Top_Job_Matches.md...")

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

            # PostgreSQL returns datetime object, not string
            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date).split(' ')[0]

            f.write(f"### {badge} [{score}/100] {title} @ {company}\n")
            f.write(f"- **AI Verdict:** {reasoning}\n")
            f.write(f"- **Apply Here:** [Link to Application]({link})\n")
            f.write(f"- *Discovered:* {date_str}\n\n")
            f.write("---\n\n")

    print(f"[+] SUCCESS: Exported {len(jobs)} jobs to Top_Job_Matches.md")
    print("    -> Open the file in VS Code and click 'Preview' to view it!")

if __name__ == "__main__":
    export_to_markdown(min_score=0)