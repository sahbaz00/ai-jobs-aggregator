import json
import ollama
import database
import re
import httpx
from bs4 import BeautifulSoup
import time
import sys
import os
from groq import Groq
from dotenv import load_dotenv
load_dotenv() # to load .env file content which we need to grab API key

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ==========================================
# PHASE 0: STATIC PROFILE LOADING
# ==========================================
def load_cv_profile():
    """Loads the static JSON CV profile from disk."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    profile_path = os.path.join(base_dir, "config", "cv_profile.json")
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[-] FATAL ERROR: {profile_path} not found. Please create it.")
        sys.exit(1)

# ==========================================
# PHASE 2: DETERMINISTIC PYTHON MATH ENGINE
# ==========================================

# The Entity Resolution Dictionary
SKILL_ALIASES = {
    "ml": "machine learning",
    "sklearn": "scikit learn",
    "scikit-learn": "scikit learn",
    "modelling": "modeling",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "postgres": "postgresql",
    "tf": "tensorflow",
    "nn": "neural network",
    "llms": "llm",
    "generative ai": "llm",
    "statistical modelling": "statistical modeling"
}

def normalize_skill(skill: str) -> str:
    """Standardizes skills by lowercasing, stripping hyphens, and mapping aliases."""
    clean_skill = skill.lower().replace("-", " ").strip()
    return SKILL_ALIASES.get(clean_skill, clean_skill)

def normalize_skills_set(skills: list) -> set:
    """Converts a list of raw skills into a standardized set."""
    return {normalize_skill(s) for s in skills}

def compute_overlap_metrics(cv_profile: dict, jd_profile: dict) -> dict:
    """Calculates overlaps between extracted JD facts and the static CV."""
    
    # Apply the new normalization engine to both CV and JD skills
    cv_skills = normalize_skills_set(cv_profile.get("skills", []))
    required = normalize_skills_set(jd_profile.get("required_skills", []))
    preferred = normalize_skills_set(jd_profile.get("preferred_skills", []))

    required_matched = cv_skills & required
    required_missing = required - cv_skills
    preferred_matched = cv_skills & preferred

    required_overlap_pct = len(required_matched) / len(required) if required else 1.0
    preferred_overlap_pct = len(preferred_matched) / len(preferred) if preferred else 0.0

    # Handle cases where JD doesn't specify experience
    min_exp = jd_profile.get("min_years_experience") or 0
    exp_delta = cv_profile.get("years_experience", 0) - min_exp

    return {
        "required_overlap_pct": round(required_overlap_pct, 2),
        "preferred_overlap_pct": round(preferred_overlap_pct, 2),
        "required_matched": list(required_matched),
        "required_missing": list(required_missing),
        "preferred_matched": list(preferred_matched),
        "experience_delta": exp_delta,
        "is_internship": jd_profile.get("is_student_or_intern", False),
        "explicit_german_required": jd_profile.get("explicit_german_required", False)
    }

def calculate_base_score(metrics: dict) -> tuple[float, list[str]]:
    """Calculates the final score based on the computed metrics."""
    score = 0.0
    reasons = []

    # 1. Required Skills (Max 50 points)
    skill_score = metrics["required_overlap_pct"] * 50
    score += skill_score
    reasons.append(f"Tech Match: {skill_score:.1f}/50")

    # 2. Preferred Skills (Max 15 points)
    pref_score = metrics["preferred_overlap_pct"] * 15
    score += pref_score

    # 3. Experience Logic (Max 20 points)
    if metrics["experience_delta"] >= 0:
        score += 20
    elif metrics["experience_delta"] == -1:
        score += 10 # 1 year short, still viable
        reasons.append("Slightly underqualified by years.")
    else:
        reasons.append("Major experience gap.")

    # 4. Student/Internship Override (The "Senior Catch" Fix)
    if metrics["is_internship"]:
        score += 20 
        reasons.append("Working Student/Intern Boost Applied (+20)")

    # 5. Language Knockout
    if metrics["explicit_german_required"]:
        score -= 40
        reasons.append("PENALTY: Fluent German explicitly required.")

    # 6. Missing Core Skills Penalty
    if metrics["required_missing"]:
        reasons.append(f"Missing Core Tech: {', '.join(metrics['required_missing'])}")

    return round(score, 1), reasons

# ==========================================
# SCRAPING UTILITY
# ==========================================
def fetch_job_description(url):
    """Fetches and cleans the job description."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        time.sleep(1.5)
        response = httpx.get(url, headers=headers, timeout=15.0, follow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        for junk in soup(['script', 'style', 'nav', 'footer', 'header', 'noscript', 'aside']):
            junk.decompose()
        main_content = soup.find('main') or soup.find('article') or soup
        text = main_content.get_text(separator=' ', strip=True)
        return re.sub(r'\s+', ' ', text)[:5000]
    except Exception as e:
        print(f"      [-] Failed to fetch description: {e}")
        return "Description could not be fetched."

# ==========================================
# MAIN ORCHESTRATOR
# ==========================================
def main():
    print("[*] Initializing V3 Hybrid Engine (Extract -> Compute -> Evaluate)...")
    
    cv_profile = load_cv_profile()
    
    try:
        with open("data/multi_company_raw_jobs.json", "r", encoding="utf-8") as f:
            raw_jobs = json.load(f)
    except FileNotFoundError:
        print("[-] Error: multi_company_raw_jobs.json not found! Run scraper.py first.")
        return

    conn = database.init_db()
    new_jobs_to_evaluate = [job for job in raw_jobs if not database.is_job_evaluated(conn, job['link'])]

    print(f"    -> Found {len(raw_jobs)} total jobs. {len(new_jobs_to_evaluate)} are new.")
    if not new_jobs_to_evaluate:
        print("[+] No new jobs. Pipeline shutting down gracefully.")
        return

    # Load the Phase 1 Prompt
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(base_dir, "config", "prompt_template.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    # Define your model here (Update to what you have installed: llama3.1, qwen2.5, gemma2)
    MODEL_NAME = "llama-3.1-8b-instant" # "llama-3.3-70b-versatile"

    for job in new_jobs_to_evaluate:
        print(f"\n[*] Processing: {job['title']} at {job['company']}")
        job_description = fetch_job_description(job['link'])

        # --- PHASE 1: JD EXTRACTION (LLM Call 1) ---
        prompt = prompt_template.replace("{job_title}", job['title'])
        prompt = prompt.replace("{company}", job['company'])
        prompt = prompt.replace("{job_description}", job_description)

        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a strict data extraction API. Return only valid JSON. No explanation. No markdown."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            jd_profile = json.loads(response.choices[0].message.content)
            
            # --- PHASE 2: COMPUTE (Python Math) ---
            print("      -> [Phase 2] Computing deterministic overlap metrics...")
            metrics = compute_overlap_metrics(cv_profile, jd_profile)
            base_score, reasons = calculate_base_score(metrics)
            
            print(f"         -> Calculated Score: {base_score}")
            print(f"         -> Missing Tech: {metrics['required_missing']}")

            # --- PHASE 3: EVALUATOR (LLM Call 2) ---
            print("      -> [Phase 3] Generating contextual evaluation...")
            eval_prompt = f"""
            You are a technical recruiter. Review these computed metrics for {job['title']} at {job['company']}.
            Base Score: {base_score}/100
            Missing Skills: {metrics['required_missing']}
            Reasons: {reasons}

            Task: Write exactly TWO sentences summarizing why this candidate is or isn't a fit based on the data above.
            Do NOT output JSON. Just write the two sentences.
            """
            eval_response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a technical recruiter. Be concise and honest."},
                    {"role": "user", "content": eval_prompt}
                ],
                temperature=0.2
            )
            ai_reasoning = eval_response.choices[0].message.content.strip()
            print(f"      -> Verdict: {ai_reasoning}")

            # --- PHASE 4: STORAGE ---
            database.save_evaluation(conn, job, base_score, ai_reasoning)

        except json.JSONDecodeError:
            print(f"      [-] Extraction failed. LLM did not return valid JSON. Skipping.")
            continue
        except Exception as e:
            print(f"      [-] Error processing {job['title']}: {e}")
            if "groq" in str(e).lower() or "401" in str(e) or "api" in str(e).lower():
                print("      [!] FATAL: Groq API error. Check your GROQ_API_KEY.")
                sys.exit(1)

    print("\n[+] SUCCESS: V3 Hybrid Pipeline Complete!")

if __name__ == "__main__":
    main()