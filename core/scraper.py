import json
import time
import httpx
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import re # Make sure 're' is imported at the top of your file!
import os


# ==========================================
# 1. COMPANY-SPECIFIC PARSERS (The "Adapters")
# ==========================================

def scrape_unicredit(base_url):
    """Deterministic parser specifically built for UniCredit's HTML structure."""
    print("    -> Running custom UniCredit parser...")
    jobs = []
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    current_offset = 0
    
    # Strip existing offset from the JSON URL so we can control the pagination
    if "&jobOffset=" in base_url:
        url_no_offset = base_url.split("&jobOffset=")[0]
    else:
        url_no_offset = base_url
        
    try:
        while True:
            paginated_url = f"{url_no_offset}&jobOffset={current_offset}"
            print(f"      -> Fetching offset {current_offset}...")
            
            # Enterprise Network Retry Block
            max_retries = 3
            success = False
            for attempt in range(max_retries):
                try:
                    response = httpx.get(paginated_url, headers=headers, timeout=20.0)
                    response.raise_for_status() 
                    success = True
                    break
                except Exception as e:
                    print(f"      [-] Network hiccup (Attempt {attempt+1}/{max_retries}): {e}")
                    time.sleep(2) 
                    
            if not success:
                print("      [-] Max retries reached. Ending loop.")
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Step 1: Find all links with 'JobDetail'
            all_potential_links = soup.find_all('a', href=lambda href: href and 'JobDetail' in href)
            
            page_job_count = 0
            
            # Step 2: The Filter (Using your Recon Intelligence)
            for link in all_potential_links:
                # Grab all CSS classes attached to this link
                css_classes = link.get('class', [])
                
                # If it's a social share button, ignore it!
                if any('shareButton' in c for c in css_classes):
                    continue
                    
                title = link.get_text(strip=True)
                href = link.get('href')
                
                # Make sure it's a full URL
                if href.startswith('/'):
                    full_link = f"https://careers.unicredit.eu{href}"
                else:
                    full_link = href
                    
                # Deduplication check
                if not any(j['link'] == full_link for j in jobs):
                    jobs.append({
                        "title": title,
                        "link": full_link,
                        "company": "UniCredit"
                    })
                    page_job_count += 1
                    
            print(f"      -> Extracted {page_job_count} clean jobs from this page.")
            
            # Step 3: Pagination Check
            # We know UniCredit shows max 15 per page. If we get less, it's the end.
            if page_job_count < 15:
                print("      -> Reached the final page. Ending loop.")
                break
                
            current_offset += 15
            time.sleep(1.5) # Polite delay
            
        print(f"    -> [Success] Extracted a total of {len(jobs)} UniCredit jobs.")
        
    except KeyboardInterrupt:
        print("    [-] Process killed by user.")
    except Exception as e:
        print(f"    [-] UniCredit scraping failed: {e}")
        
    return jobs


def scrape_holidu(url):
    """Hybrid parser: Extracts ALL relevant tech/data jobs (bypassing Load More) with perfect URLs."""
    print("    -> Running custom Holidu parser...")
    jobs = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        response = httpx.get(url, headers=headers, timeout=15.0)
        response.raise_for_status()
        
        # PASS 1: DOM Extraction (Harvesting Ground-Truth URLs for the visible jobs)
        soup = BeautifulSoup(response.text, 'html.parser')
        dom_links = {}
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href.startswith('/careers/') and 'list' not in href:
                title_tag = link.find('h3')
                if title_tag:
                    clean_title = title_tag.get_text(strip=True)
                    dom_links[clean_title.lower()] = f"https://www.holidu.com{href}"
                    
        # PASS 2: JSON Extraction (Harvesting ALL jobs from the hidden React state)
        pattern = r'"id":"([^"]+)","jobTitle":"([^"]+)","department":"([^"]+)".*?"office":"([^"]+)"'
        matches = re.findall(pattern, response.text)
        
        for job_id, title, department, location in matches:
            clean_title = title.encode('utf-8').decode('unicode_escape')
            t_lower = clean_title.lower()
            
            # THE SENIOR PIVOT: No more hardcoded keyword lists!
            # We use your global funnel so we don't miss future "AI" or "Automation" roles.
            if is_relevant_job(clean_title, department):
                
                # PASS 3: RECONCILIATION
                if t_lower in dom_links:
                    # Visible job = perfect HTML link
                    full_link = dom_links[t_lower]
                else:
                    # Hidden job = simulated frontend routing
                    slug = re.sub(r'[^a-z0-9]+', '-', t_lower).strip('-')
                    full_link = f"https://www.holidu.com/careers/{slug}"
                    
                # Deduplication check
                if not any(j['id'] == job_id for j in jobs):
                    jobs.append({
                        "id": job_id, 
                        "title": clean_title, 
                        "location": location,
                        "link": full_link,
                        "company": "Holidu"
                    })
                    
        for j in jobs:
            j.pop('id', None)

        print(f"    -> [Success] Extracted {len(jobs)} Holidu jobs with wide-net discovery.")
        
    except Exception as e:
        print(f"    [-] Holidu scraping failed: {e}")
        
    return jobs


def scrape_sap(base_url):
    """Deterministic parser specifically built for SAP SuccessFactors HTML structure."""
    print("    -> Running custom SAP parser...")
    jobs = []
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    current_offset = 0
    
    # Ensure we don't double-stack the startrow parameter if it's already in the URL
    if "&startrow=" in base_url:
        url_no_offset = base_url.split("&startrow=")[0]
    else:
        url_no_offset = base_url
        
    try:
        while True:
            # SAP uses 'startrow' for pagination (0, 25, 50...)
            paginated_url = f"{url_no_offset}&startrow={current_offset}"
            print(f"      -> Fetching offset {current_offset}...")
            
            # Enterprise Network Retry Block
            max_retries = 3
            success = False
            for attempt in range(max_retries):
                try:
                    response = httpx.get(paginated_url, headers=headers, timeout=20.0)
                    response.raise_for_status() 
                    success = True
                    break
                except Exception as e:
                    print(f"      [-] Network hiccup (Attempt {attempt+1}/{max_retries}): {e}")
                    time.sleep(2) 
                    
            if not success:
                print("      [-] Max retries reached. Ending loop.")
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # THE FILTER: Using the exact CSS class from your Reconnaissance!
            job_links = soup.find_all('a', class_='jobTitle-link')
            
            page_job_count = len(job_links)
            
            # The Infinite Loop Protector:
            # Because SAP's ">>" button is broken, we ignore it. If we find 0 jobs, we are done.
            if page_job_count == 0:
                print("      -> No more jobs found on this page. Reached the end.")
                break
                
            for link in job_links:
                title = link.get_text(strip=True)
                href = link.get('href')
                
                # SAP uses relative URLs, so we attach the base domain
                if href.startswith('/'):
                    full_link = f"https://jobs.sap.com{href}"
                else:
                    full_link = href
                    
                # Deduplication check
                if not any(j['link'] == full_link for j in jobs):
                    jobs.append({
                        "title": title,
                        "link": full_link,
                        "company": "SAP" # Hardcoded tag for downstream AI evaluation
                    })
                    
            print(f"      -> Extracted {page_job_count} jobs from this page.")
            
            # Advance to the next page (SAP defaults to 25 per page)
            current_offset += 25
            time.sleep(1.5) # Polite delay
            
        print(f"    -> [Success] Extracted a total of {len(jobs)} SAP jobs.")
        
    except KeyboardInterrupt:
        print("    [-] Process killed by user.")
    except Exception as e:
        print(f"    [-] SAP scraping failed: {e}")
        
    return jobs



def scrape_join(raw_url):
    """Universal parser for JOIN ATS using a Recursive JSON Hydration Crawler."""
    
    # THE SENIOR FIX: Automatically strip query parameters so we always hit the stable base URL
    base_url = raw_url.split('?')[0].rstrip('/')
    company_slug = base_url.split('/')[-1]
    company_name = company_slug.replace('-', ' ').title()
    
    print(f"    -> Running Universal JOIN parser for {company_name}...")
    jobs = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    page = 1
    
    def find_jobs(obj):
        tech_count = 0
        raw_count = 0
        
        if isinstance(obj, dict):
            if 'title' in obj and isinstance(obj['title'], str):
                title = obj['title']
                slug = None
                
                for val in obj.values():
                    if isinstance(val, str) and re.match(r'^\d{6,}-[a-zA-Z0-9-]+$', val):
                        slug = val
                        break
                        
                if slug:
                    raw_count += 1 
                    
                    # STAGE 1 FUNNEL: Use our central heuristic brain instead of hardcoded keywords!
                    # Make sure you pasted the is_relevant_job() function at the top of your file!
                    if is_relevant_job(title):
                        full_link = f"https://join.com/companies/{company_slug}/{slug}"
                        
                        print(f"      [DEBUG] Found slug: {slug} for title: {title}")  # ← ADD THIS
                        
                        if not any(j['link'] == full_link for j in jobs):
                            jobs.append({
                                "title": title,
                                "link": full_link,
                                "company": company_name
                            })
                            tech_count += 1
                            
            for v in obj.values():
                t, r = find_jobs(v)
                tech_count += t
                raw_count += r
                
        elif isinstance(obj, list):
            for item in obj:
                t, r = find_jobs(item)
                tech_count += t
                raw_count += r
                
        return tech_count, raw_count

    try:
        while True:
            # We control the pagination safely ourselves
            paginated_url = f"{base_url}?page={page}"
            print(f"      -> Fetching page {page}...")
            
            max_retries = 3
            success = False
            for attempt in range(max_retries):
                try:
                    response = httpx.get(paginated_url, headers=headers, timeout=20.0)
                    response.raise_for_status()
                    success = True
                    break
                except Exception as e:
                    print(f"      [-] Network hiccup (Attempt {attempt+1}/{max_retries}): {e}")
                    time.sleep(2)
                    
            if not success:
                print("      [-] Max retries reached. Ending loop.")
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            next_data_script = soup.find('script', id='__NEXT_DATA__')
            tech_jobs, raw_jobs = 0, 0
            
            if next_data_script:
                try:
                    json_data = json.loads(next_data_script.string)
                    jobs_before_page = len(jobs)        # ← measure BEFORE
                    tech_jobs, raw_jobs = find_jobs(json_data)
                    jobs_after_page = len(jobs)         # ← measure AFTER
                except json.JSONDecodeError:
                    print("      [-] Error decoding JSON data.")
            else:
                print("      [-] Could not find __NEXT_DATA__ script. The site architecture changed.")
                break
                
            print(f"      -> Scanned {raw_jobs} total jobs, saved {tech_jobs} Data/Tech jobs.")
            
            if raw_jobs == 0:
                print("      -> No more jobs found on this page. Reached the end.")
                break

            # Stop if this page added zero NEW unique jobs
            if jobs_after_page == jobs_before_page:
                print("      -> No new unique jobs found. Pagination complete.")
                break
                
            page += 1
            time.sleep(1.5) 
            
        print(f"    -> [Success] Extracted a total of {len(jobs)} {company_name} jobs.")
        
    except KeyboardInterrupt:
        print("    [-] Process killed by user.")
    except Exception as e:
        print(f"    [-] JOIN scraping failed: {e}")
        
    return jobs



def scrape_siemens(raw_url):
    """Deterministic parser specifically built for Siemens' enterprise ATS structure."""
    print("    -> Running custom Siemens parser...")
    jobs = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    # Dynamically extract their pagination step (e.g., folderRecordsPerPage=6)
    import re
    step_match = re.search(r'folderRecordsPerPage=(\d+)', raw_url)
    pagination_step = int(step_match.group(1)) if step_match else 6
    
    # Strip any existing offset so we can control the loop
    if "&folderOffset=" in raw_url:
        base_url = raw_url.split("&folderOffset=")[0]
    else:
        base_url = raw_url
        
    # Ensure URL ends correctly before we append our offset
    if not base_url.endswith('&') and not base_url.endswith('?'):
        base_url += '&'
        
    current_offset = 0
    
    try:
        while True:
            paginated_url = f"{base_url}folderOffset={current_offset}"
            print(f"      -> Fetching offset {current_offset}...")
            
            # Enterprise Network Retry Block
            max_retries = 3
            success = False
            for attempt in range(max_retries):
                try:
                    response = httpx.get(paginated_url, headers=headers, timeout=20.0)
                    response.raise_for_status() 
                    success = True
                    break
                except Exception as e:
                    print(f"      [-] Network hiccup (Attempt {attempt+1}/{max_retries}): {e}")
                    time.sleep(2) 
                    
            if not success:
                print("      [-] Max retries reached. Ending loop.")
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Identify all potential job links using your Recon HTML
            # We look for 'JobDetail' in the href, just like UniCredit
            all_potential_links = soup.find_all('a', href=lambda href: href and 'JobDetail' in href)
            
            raw_page_job_count = 0
            tech_page_job_count = 0
            
            for link in all_potential_links:
                css_classes = link.get('class', [])
                
                # Filter out hidden social share buttons (if Siemens uses them like UniCredit)
                if any('share' in c.lower() for c in css_classes):
                    continue
                    
                title = link.get_text(strip=True)
                href = link.get('href')
                
                if not title: # Skip empty links
                    continue
                    
                raw_page_job_count += 1
                
                # Build absolute URL
                if href.startswith('/'):
                    full_link = f"https://jobs.siemens.com{href}"
                else:
                    full_link = href
                    
                # STAGE 1 FUNNEL: Apply our central AI-prep heuristic
                if is_relevant_job(title):
                    # Deduplication check
                    if not any(j['link'] == full_link for j in jobs):
                        jobs.append({
                            "title": title,
                            "link": full_link,
                            "company": "Siemens"
                        })
                        tech_page_job_count += 1
                        
            print(f"      -> Scanned {raw_page_job_count} raw links, saved {tech_page_job_count} Data/Tech jobs.")
            
            # Pagination Check: If the ATS returned fewer jobs than the max per page, we are done
            # (Or if it returned 0 raw links, meaning an empty page)
            if raw_page_job_count < pagination_step:
                print("      -> Reached the final page. Ending loop.")
                break
                
            current_offset += pagination_step
            time.sleep(1.5) 
            
        print(f"    -> [Success] Extracted a total of {len(jobs)} Siemens Data/Tech jobs.")
        
    except KeyboardInterrupt:
        print("    [-] Process killed by user.")
    except Exception as e:
        print(f"    [-] Siemens scraping failed: {e}")
        
    return jobs


# ==========================================
# 2. THE ROUTER REGISTRY
# ==========================================
# Map the company names from companies.json to their specific Python functions
SCRAPER_REGISTRY = {
    "UniCredit": scrape_unicredit,
    "Holidu": scrape_holidu,
    "SAP": scrape_sap,
    "Delicious-Data": scrape_join,
    "JOIN": scrape_join,
    "SIEMENS":scrape_siemens
}


# ==========================================
# IS_RELEVANT_JOB
# ==========================================

def is_relevant_job(title, department=""):
    """
    A Wide-Funnel Heuristic Filter to maximize recall for tech/data roles
    while blocking obvious irrelevant departments.
    """
    t_lower = title.lower()
    d_lower = department.lower()
    combined_text = f"{t_lower} {d_lower}"
    
    # THE BLOCK-LIST: Instantly reject obvious non-tech roles
    # This saves us from extracting 100s of useless jobs.
    block_keywords = [
        'hr', 'human resources', 'recruiter', 'talent', 'sales', 'account executive', 
        'marketing manager', 'legal', 'counsel', 'nurse', 'driver', 'warehouse', 
        'facility', 'payroll', 'tax', 'compliance'
    ]
    
    if any(b in combined_text for b in block_keywords):
        return False

    # THE WIDE ALLOW-LIST: Catch anything remotely related to our field
    # We include software engineering because Data Science overlaps heavily with Backend/Cloud.
    allow_keywords = [
        'data', 'analytics', 'machine learning', ' ai ', '-ai-', 'artificial intelligence', 
        ' bi ', '-bi-', 'business intelligence', 'engineer', 'scientist', 'quant', 
        'algorithm', 'python', 'sql', 'developer', 'software', 'backend', 'cloud', 
        'infrastructure', 'architect', 'insight', 'vision', 'nlp', 'llm'
    ]
    
    # If it has a tech keyword and wasn't blocked, we keep it!
    if any(a in combined_text for a in allow_keywords):
        return True
        
    return False


# ==========================================
# 3. THE MASTER PIPELINE
# ==========================================
def run_daily_pipeline():
    print("[*] Initializing Deterministic Job Aggregator...")
    
    try:
        with open("config/companies.json", "r") as f:
            targets = json.load(f)
    except FileNotFoundError:
        print("[-] Error: companies.json not found.")
        return

    all_raw_jobs = []
    seen_urls = set()

    # Route the Tasks
    for company in targets:
        if company.get("is_active"):
            name = company["name"]
            url = company["careers_url"]
            
            print(f"\n[*] Target Acquired: {name}")
            
            if name in SCRAPER_REGISTRY:
                scraper_function = SCRAPER_REGISTRY[name]
                company_jobs = scraper_function(url)
                for job in company_jobs:
                    if job['link'] not in seen_urls:
                        seen_urls.add(job['link'])
                        all_raw_jobs.append(job)
            else:
                print(f"    [-] Warning: No custom parser built yet for {name}. Skipping.")
        else:
            print(f"[*] Skipping {company['name']} (Inactive)")

    # Save the aggregated raw data
    print(f"\n[*] Pipeline Complete. Total raw jobs collected: {len(all_raw_jobs)}")
    
    os.makedirs("data", exist_ok=True)
    with open("data/multi_company_raw_jobs.json", "w", encoding="utf-8") as f:
        json.dump(all_raw_jobs, f, indent=4, ensure_ascii=False)
        
    print("[+] Raw data saved to multi_company_raw_jobs.json.")
    print("[+] Ready for AI Evaluation Phase.")

if __name__ == "__main__":
    run_daily_pipeline()