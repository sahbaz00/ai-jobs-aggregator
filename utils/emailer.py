import smtplib
import os
import sqlite3
from email.message import EmailMessage
from dotenv import load_dotenv
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

def send_daily_digest():
    """Generates a native HTML email directly from the database and sends it."""
    print("[*] Initializing HTML Email Engine...")
    load_dotenv()
    
    sender_email = os.getenv("SENDER_EMAIL")
    app_password = os.getenv("EMAIL_PASSWORD")
    receiver_email = os.getenv("RECEIVER_EMAIL")
    
    if not all([sender_email, app_password, receiver_email]):
        print("[-] Error: Missing email credentials in .env file.")
        return False

    # Pathing: Up to root, down to data folder
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "data", "jobs_state.db")

    if not os.path.exists(db_path):
        print("[-] Error: Database not found. Run the pipeline first.")
        return False

    # THE SENIOR MOVE: Calculate today's date
    today_str = datetime.now().strftime('%Y-%m-%d')

    # Query the database for high-quality jobs discovered ONLY today
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # The ? is a parameterized query to protect against SQL injection
        # We use LIKE '2026-03-22%' to catch any time of day it was scraped
        cursor.execute("""
            SELECT title, company, ai_score, ai_reasoning, url, date_discovered 
            FROM evaluated_jobs 
            WHERE ai_score >= 40 
            AND date_discovered LIKE ?
            ORDER BY ai_score DESC
        """, (f"{today_str}%",))
        
        jobs = cursor.fetchall()
        conn.close()
    except sqlite3.Error as e:
        print(f"[-] Database Error: {e}")
        return False

    if not jobs:
        print(f"[*] No new high-scoring jobs found for {today_str}. Skipping email.")
        return True

    # Constructing the HTML Table
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <h2 style="color: #2c3e50;">🚀 AI Job Aggregator: Daily Matches</h2>
        <p>Found <b>{len(jobs)}</b> new high-scoring jobs for <b>{today_str}</b>.</p>
        <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
          <thead>
            <tr style="background-color: #f8f9fa; border-bottom: 2px solid #dee2e6; text-align: left;">
              <th style="padding: 12px; width: 80px;">Score</th>
              <th style="padding: 12px; width: 250px;">Role & Company</th>
              <th style="padding: 12px;">AI Verdict</th>
            </tr>
          </thead>
          <tbody>
    """

    # Unpack the new date_discovered variable in the loop
    for title, company, score, reasoning, url, date_discovered in jobs:
        color = "#28a745" if score >= 90 else "#d4a017" # Green for 90+, Gold for 40-89
        
        # --- THE TIMEZONE TRANSLATOR ---
        try:
            # 1. Convert the DB string into a Python datetime object
            utc_dt = datetime.strptime(date_discovered, "%Y-%m-%d %H:%M:%S")
            
            # 2. Explicitly tell Python this object is in UTC
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
            
            # 3. Force conversion to German time, ignoring the AWS server's local clock
            local_dt = utc_dt.astimezone(ZoneInfo("Europe/Berlin"))
            
            # 4. Turn it back into a string for the email HTML
            display_time = local_dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            # Fallback just in case the database format is slightly different
            display_time = date_discovered
            
        html_content += f"""
            <tr style="border-bottom: 1px solid #eee;">
              <td style="padding: 12px; font-weight: bold; color: {color};">{score}/100</td>
              <td style="padding: 12px;">
                <a href="{url}" style="color: #0056b3; text-decoration: none; font-weight: bold;">{title}</a><br>
                <span style="font-size: 0.9em; color: #6c757d;">@ {company}</span><br>
                <span style="font-size: 0.8em; color: #999;">Found: {display_time}</span>
              </td>
              <td style="padding: 12px; font-size: 0.9em; color: #495057;">{reasoning}</td>
            </tr>
        """

    html_content += """
          </tbody>
        </table>
        <p style="font-size: 0.8em; color: #999; margin-top: 20px;">Automated by Shahbaz's MLOps Pipeline.</p>
      </body>
    </html>
    """

    # Construct the Email Object
    msg = EmailMessage()
    msg['Subject'] = f'🚀 {len(jobs)} High-Scoring AI Job Matches'
    msg['From'] = sender_email
    msg['To'] = receiver_email
    
    # Set fallback text, then add the beautiful HTML
    msg.set_content("Please enable HTML to view this email.")
    msg.add_alternative(html_content, subtype='html')

    print(f"[*] Connecting to SMTP server to email {receiver_email}...")
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)
        print("[+] SUCCESS: HTML Daily digest delivered to your inbox!")
        return True
    except Exception as e:
        print(f"[-] Failed to send email: {e}")
        return False


def send_error_alert(failed_step, error_traceback):
    """Sends a high-priority plain-text alert if the pipeline crashes."""
    print(f"[*] Dispatching critical error alert for: {failed_step}...")
    load_dotenv()
    
    sender_email = os.getenv("SENDER_EMAIL")
    app_password = os.getenv("EMAIL_PASSWORD")
    receiver_email = os.getenv("RECEIVER_EMAIL")
    
    if not all([sender_email, app_password, receiver_email]):
        print("[-] Error: Missing email credentials. Cannot send alert.")
        return False

    msg = EmailMessage()
    msg['Subject'] = f'⚠️ PIPELINE CRASH: {failed_step}'
    msg['From'] = sender_email
    msg['To'] = receiver_email
    
    body = f"""
    The AI Job Aggregator pipeline encountered a fatal error and halted.
    
    FAILED STEP: {failed_step}
    
    ERROR TRACEBACK:
    {error_traceback}
    
    Please check the server logs.
    """
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)
        print("[+] SUCCESS: Error alert delivered to your inbox.")
        return True
    except Exception as e:
        print(f"[-] Failed to send error alert: {e}")
        return False


if __name__ == "__main__":
    send_daily_digest()