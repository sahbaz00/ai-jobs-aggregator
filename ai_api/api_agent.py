import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Open the vault to get our API key
load_dotenv()

# ==========================================
# 1. THE CONTRACT (Pydantic Schema)
# We force the LLM to reply exactly in this format. No chatting allowed.
# ==========================================
class JobEvaluation(BaseModel):
    title: str
    link: str
    match_score: int = Field(description="Score from 0 to 100 based on fit")
    verdict: str = Field(description="One short sentence explaining why it is a fit or a skip")
    recommended: bool = Field(description="True ONLY if score is >= 75")

class JobReport(BaseModel):
    jobs: list[JobEvaluation]

# ==========================================
# 2. THE ENGINE
# ==========================================
def evaluate_jobs():
    print("[*] Loading raw jobs from JSON...")
    try:
        with open("unicredit_raw_jobs.json", "r", encoding="utf-8") as f:
            raw_jobs = json.load(f)
    except FileNotFoundError:
        print("[-] Error: unicredit_raw_jobs.json not found! Run scraper.py first.")
        return

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "your_actual_key_here":
        print("[-] Error: GEMINI_API_KEY is missing or invalid in the .env file.")
        return

    # Initialize the modern Gemini Client
    client = genai.Client(api_key=api_key)

    # ==========================================
    # 3. THE BRAIN (System Prompt)
    # Notice how we hardcode the specific parameters of your career trajectory
    # ==========================================
    candidate_profile = """
    Candidate Profile:
    - Current Master of Data Science student at KU Eichstätt-Ingolstadt.
    - Previous experience as a Data Scientist in the banking sector (Kapital Bank).
    - Background in Computer Information Systems.
    - Goal: Seeking industry-focused working student (Werkstudent) or internship roles in Germany.
    - Focus: Highly interested in AI, Machine Learning, and Data Science. Less interested in pure finance/sales roles unless they heavily involve data analytics.
    """

    prompt = f"""
    You are an elite technical recruiter. Analyze the following list of job postings.
    Cross-reference them against this candidate's profile:
    {candidate_profile}

    Evaluate every single job based on how well it fits this candidate. 
    Return a structured JSON response scoring each job.
    
    Jobs to evaluate:
    {json.dumps(raw_jobs, indent=2)}
    """

    print(f"[*] Sending {len(raw_jobs)} jobs to Gemini AI for evaluation. This may take 5-10 seconds...")
    
    try:
        # We use gemini-2.0-flash because it is lightning fast and great at structured JSON
        response = client.models.generate_content(
            model='models/gemini-flash-latest',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=JobReport,
                temperature=0.1, # Low temperature means strict, logical grading
            ),
        )
        
        # Save the AI's output to a new file
        with open("evaluated_jobs.json", "w", encoding="utf-8") as f:
            # We parse and re-dump to ensure it formats beautifully in VS Code
            parsed_json = json.loads(response.text)
            json.dump(parsed_json, f, indent=4, ensure_ascii=False)
            
        print("\n[+] Success! The AI has spoken. Results saved to evaluated_jobs.json")
        
    except Exception as e:
        print(f"[-] An error occurred during AI evaluation: {e}")

if __name__ == "__main__":
    evaluate_jobs()