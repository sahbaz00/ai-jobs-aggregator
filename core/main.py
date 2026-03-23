import subprocess
import os
import sys
import logging
from datetime import datetime

# Dynamically add the project root to the path so we can import our emailer
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)
from utils.emailer import send_error_alert

# Ensure a logs directory exists
log_dir = os.path.join(base_dir, "logs")
os.makedirs(log_dir, exist_ok=True)

# Configure the "Black Box" flight recorder
log_file = os.path.join(log_dir, "pipeline.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def run_pipeline():
    """Executes the pipeline sequentially with full error catching and alerting."""
    start_msg = "🚀 STARTING DAILY AI JOB PIPELINE 🚀"
    print(f"\n{'='*50}\n {start_msg}\n{'='*50}\n")
    logging.info(start_msg)

    steps = [
        ("Phase 1: Web Scraping", [sys.executable, "core/scraper.py"]),
        ("Phase 2: AI Evaluation", [sys.executable, "core/agent.py"]),
        ("Phase 2.1: DB check", [sys.executable, "utils/inspect_db.py"]),
        ("Phase 2.1: DB view", [sys.executable, "utils/db_viewer.py"]),
        ("Phase 3: Email Dispatch", [sys.executable, "utils/emailer.py"])
    ]

    try:
        for step_name, command in steps:
            print(f">>> Executing {step_name} <<<")
            logging.info(f"Starting {step_name}...")
            
            try:
                result = subprocess.run(
                    command, 
                    cwd=base_dir, 
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                print(result.stdout)
                logging.info(f"{step_name} completed successfully.\n{result.stdout}")
                
            except subprocess.CalledProcessError as e:
                # Grab both stdout (print statements) and stderr (tracebacks)
                error_msg = f"Fatal Error in {step_name}.\nExit Code: {e.returncode}\n\nLast Output:\n{e.stdout}\n\nError Traceback:\n{e.stderr}"
                
                print(f"\n[-] PIPELINE HALTED: {error_msg}")
                logging.error(error_msg)
                
                # Send the fully detailed error to the email alert
                send_error_alert(step_name, error_msg)
                
                sys.exit(1)

        success_msg = "✅ PIPELINE COMPLETED SUCCESSFULLY ✅"
        print(f"\n{'='*50}\n {success_msg}\n{'='*50}\n")
        logging.info(success_msg)

    finally:
        # THE SENIOR SEPARATOR
        # This block is guaranteed to run, even if sys.exit(1) is called above!
        separator = "=" * 80
        logging.info(f"END OF RUN\n{separator}\n")

if __name__ == "__main__":
    run_pipeline()