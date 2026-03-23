import json
import ollama
import database
import re
import httpx
from bs4 import BeautifulSoup
import time
import sys
import os

def load_candidate_profile():
    """Reads the external markdown profile."""
    try:
        with open("config/candidate_profile.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print("[-] Error: candidate_profile.md not found. Please create it.")
        return None

def calculate_deterministic_score(json_data):
    """Calculates the job score deterministically based on extracted JSON facts."""
    score = 100
    verdict_reasons = []

    # 1. Seniority Check (Python does the math)
    if json_data.get('is_senior_role', False):
        score -= 60
        verdict_reasons.append("Seniority mismatch")

    # 2. Language Check
    if json_data.get('explicit_german_required', False):
        score -= 40
        verdict_reasons.append("German language requirement not met")

    # 3. Tech Stack Check
    missing_skills = json_data.get('missing_core_tech_skills', [])
    if missing_skills:
        penalty = len(missing_skills) * 15
        score -= penalty
        verdict_reasons.append(f"Missing skills: {', '.join(missing_skills)}")

    # 4. Student Bonus
    if json_data.get('is_student_or_intern', False):
        score += 20
        verdict_reasons.append("Working Student/Intern bonus applied")

    # 5. Dynamic Verdict Generation
    if score >= 70:
        verdict = "Strong match based on technical skills and requirements."
    else:
        reason_str = " | ".join(verdict_reasons) if verdict_reasons else "Lacks core requirements."
        verdict = f"Rejected: {reason_str}"

    return score, verdict

def fetch_job_description(url):
    """
    Universally fetches and cleans the main text of a job description page.
    Strips out menus, scripts, and footers to save AI context tokens.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        time.sleep(1.5) # Polite delay so we don't trigger anti-bot defenses
        response = httpx.get(url, headers=headers, timeout=15.0, follow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # SENIOR HACK 1: Destroy the junk HTML tags before extracting text
        for junk in soup(['script', 'style', 'nav', 'footer', 'header', 'noscript', 'aside']):
            junk.decompose()
            
        # Target the main content area (ATS platforms usually use these tags)
        main_content = soup.find('main') or soup.find('article') or soup
        
        # Extract the pure text and normalize the spacing
        text = main_content.get_text(separator=' ', strip=True)
        clean_text = re.sub(r'\s+', ' ', text)
        
        # SENIOR HACK 2: Truncate to ~5000 characters to protect Llama 3's context window
        return clean_text[:5000]
        
    except Exception as e:
        print(f"      [-] Failed to fetch description: {e}")
        return "Description could not be fetched. Evaluate based on title and company."

def main():
    print("[*] Initializing Local AI Evaluation Agent...")

    profile_text = load_candidate_profile()
    if not profile_text:
        return

    try:
        with open("data/multi_company_raw_jobs.json", "r", encoding="utf-8") as f:
            raw_jobs = json.load(f)
    except FileNotFoundError:
        print("[-] Error: multi_company_raw_jobs.json not found! Run scraper.py first.")
        return

    print("[*] Connecting to local SQLite state database...")
    conn = database.init_db()
    new_jobs_to_evaluate = []

    print("[*] Calculating job delta (filtering out already evaluated jobs)...")
    for job in raw_jobs:
        if not database.is_job_evaluated(conn, job['link']):
            new_jobs_to_evaluate.append(job)

    print(f"    -> [Result] Found {len(raw_jobs)} total jobs. {len(new_jobs_to_evaluate)} are new.")

    if not new_jobs_to_evaluate:
        print("[+] No new jobs to evaluate today. Pipeline shutting down gracefully.")
        return

    print("\n[*] Starting Local AI Deep Evaluation with Candidate Context...")
    
    for job in new_jobs_to_evaluate:
        print(f"\n[*] Deep Analyzing: {job['title']} at {job['company']}")
        print(f"      -> Fetching full description from source...")
        
        # THE NEW DEEP FETCH INTEGRATION
        job_description = fetch_job_description(job['link'])
        
        # prompt = f"""
        # You are a highly literal, rigorous technical recruiter. You evaluate candidates based STRICTLY on the text provided. Do not invent requirements. Do not assume. 

        # === CANDIDATE PROFILE ===
        # {profile_text}
        
        # === JOB LISTING ===
        # Company: {job['company']}
        # Job Title: {job['title']}
        # Job Description: {job_description}
        
        # === SCORING RUBRIC (START AT 100 POINTS) ===
        # RULE 1 (STUDENT BOOST): If the Job Title contains "Working Student", "Werkstudent", or "Intern", ADD 20 POINTS.
        
        # RULE 2 (SENIOR PENALTY): If the Job Title contains "Senior", "Lead", "Head", or asks for 3+ years experience, DEDUCT 50 POINTS.
        
        # RULE 3 (LANGUAGE PENALTY): If the JOB DESCRIPTION explicitly requires "Native/Fluent/C1 German", DEDUCT 30 POINTS. If the job description is in English and does not explicitly demand German, Make NO deduction.
        
        # RULE 4 (TECH PENALTY): Deduct 5 points for every core technical skill required by the job that is explicitly MISSING from the candidate profile. Check the profile carefully (The candidate HAS Python, Pandas, Scikit-learn, PyTorch, SQL, etc.).
        
        # === INSTRUCTIONS ===
        # You MUST think step-by-step. First, write a brief WORKSHEET analyzing each rule. Then, calculate the SCORE.
        
        # You must reply using EXACTLY this format and nothing else:
        # WORKSHEET:
        # - Rule 1: [Your observation] -> [Points]
        # - Rule 2: [Your observation] -> [Points]
        # - Rule 3: [Your observation] -> [Points]
        # - Rule 4: [Your observation] -> [Points]
        
        # SCORE: [Final Calculated Number]
        # VERDICT: [One sentence summary]
        # """
        
        # --- DYNAMIC PROMPT INJECTION ---
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt_path = os.path.join(base_dir, "config", "prompt_template.txt")
        
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
        except FileNotFoundError:
            print(f"    [-] FATAL ERROR: {prompt_path} not found!")
            sys.exit(1)
        
        # Using .replace() instead of .format() to avoid JSON bracket clashes
        prompt = prompt_template.replace("{profile_text}", profile_text)
        prompt = prompt.replace("{job_title}", job['title'])
        prompt = prompt.replace("{company}", job['company'])
        prompt = prompt.replace("{job_description}", job_description)

        try:
            print(f"      -> Handing off to LLM for structured JSON extraction...")
            
            # --- THE UPGRADED ENGINE ---
            # Notice format='json' and temperature=0.0
            response = ollama.generate(
                model='llama3:8b', 
                prompt=prompt,
                format='json', 
                options={'temperature': 0.0}
            )
            
            ai_text = response['response'].strip()
            
            # Print the raw JSON to terminal so we can see the LLM's "brain"
            print(f"\n--- RAW LLM JSON ---\n{ai_text}\n----------------------\n")
            
            try:
                # Python converts the text string into a real dictionary
                extracted_data = json.loads(ai_text)
                
                # Python calculates the perfect score
                score, verdict = calculate_deterministic_score(extracted_data)
                
                print(f"    -> [DETERMINISTIC SCORE]: {score}")
                print(f"    -> [VERDICT]: {verdict}")
                
                # Save state to Database so we never evaluate this URL again
                database.save_evaluation(conn, job, score, verdict)
                
            except json.JSONDecodeError as e:
                print(f"    [-] FATAL ERROR: LLM failed to output valid JSON. Output was: {ai_text}")
                print(f"    [-] JSON Error details: {e}")
                # Skip saving to DB so it tries again next run
                continue

        except Exception as e:
            print(f"    [-] Error evaluating {job['title']}: {e}")
            
            # THE KILL SWITCH
            if "Failed to connect to Ollama" in str(e) or "ConnectionRefusedError" in str(e):
                print("    [!] FATAL: LLM Engine offline. Aborting agent.py...")
                sys.exit(1)

    print("\n[+] SUCCESS: AI Evaluation Delta Run Complete!")

if __name__ == "__main__":
    main()