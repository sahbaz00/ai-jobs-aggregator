import smtplib
import os
import sys
import psycopg2
from email.message import EmailMessage
from dotenv import load_dotenv
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import mark_jobs_as_sent

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path=dotenv_path)

def send_daily_digest():
    """Generates a native HTML email directly from Supabase and sends it."""
    print("[*] Initializing HTML Email Engine...")

    sender_email = os.getenv("SENDER_EMAIL")
    app_password = os.getenv("EMAIL_PASSWORD")
    receiver_email = os.getenv("RECEIVER_EMAIL")
    database_url = os.getenv("SUPABASE_DB_URL")

    if not all([sender_email, app_password, receiver_email]):
        print("[-] Error: Missing email credentials in .env file.")
        return False

    if not database_url:
        print("[-] Error: SUPABASE_DB_URL not found in .env file.")
        return False

    today_str = datetime.now().strftime('%Y-%m-%d')

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT title, company, ai_score, ai_reasoning, url, date_discovered
            FROM evaluated_jobs
            WHERE ai_score >= 40
            AND email_sent = FALSE
            ORDER BY ai_score DESC
        """)

        jobs = cursor.fetchall()
        cursor.close()
        # ← DO NOT close conn here anymore, needed later for mark_jobs_as_sent

    except psycopg2.Error as e:
        print(f"[-] Database Error: {e}")
        return False

    if not jobs:
        print(f"[*] No unsent high-scoring jobs found. Skipping email.")
        conn.close()
        return True

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

    for title, company, score, reasoning, url, date_discovered in jobs:
        color = "#28a745" if score >= 90 else "#d4a017"

        # PostgreSQL returns date_discovered as a real datetime object
        # No need to parse it — just convert timezone directly
        try:
            if hasattr(date_discovered, 'astimezone'):
                # Already a datetime object from PostgreSQL
                if date_discovered.tzinfo is None:
                    date_discovered = date_discovered.replace(tzinfo=timezone.utc)
                local_dt = date_discovered.astimezone(ZoneInfo("Europe/Berlin"))
            else:
                # Fallback: parse as string
                utc_dt = datetime.strptime(str(date_discovered), "%Y-%m-%d %H:%M:%S")
                utc_dt = utc_dt.replace(tzinfo=timezone.utc)
                local_dt = utc_dt.astimezone(ZoneInfo("Europe/Berlin"))

            display_time = local_dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            display_time = str(date_discovered)

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

    msg = EmailMessage()
    msg['Subject'] = f'🚀 {len(jobs)} High-Scoring AI Job Matches'
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg.set_content("Please enable HTML to view this email.")
    msg.add_alternative(html_content, subtype='html')

    print(f"[*] Connecting to SMTP server to email {receiver_email}...")
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)

        # Only mark as sent AFTER email confirmed delivered
        sent_urls = [job[4] for job in jobs]  # url is index 4
        mark_jobs_as_sent(conn, sent_urls)
        print(f"    -> Marked {len(sent_urls)} jobs as sent in database.")

        print("[+] SUCCESS: HTML Daily digest delivered to your inbox!")
        return True

    except Exception as e:
        print(f"[-] Failed to send email: {e}")
        # DO NOT mark as sent if email failed
        return False

    finally:
        conn.close()  # ← always close connection at the very end


def send_error_alert(failed_step, error_traceback):
    """Sends a high-priority plain-text alert if the pipeline crashes."""
    print(f"[*] Dispatching critical error alert for: {failed_step}...")

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
    msg.set_content(f"""
The AI Job Aggregator pipeline encountered a fatal error and halted.

FAILED STEP: {failed_step}

ERROR TRACEBACK:
{error_traceback}

Please check the server logs.
    """)

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