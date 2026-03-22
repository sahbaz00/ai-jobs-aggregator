import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import time
import json

load_dotenv()

def scrape_job_details(job_url):
    """Visits a specific job page and extracts the description text."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    try:
        response = httpx.get(job_url, headers=headers, timeout=10.0)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # On UniCredit's site, the description is usually in a div with this class:
            # Note: We use a general search if the specific class isn't found
            desc_section = soup.find('div', class_='job__details__content')
            
            if desc_section:
                return desc_section.get_text(separator=' ', strip=True)
            else:
                # Fallback: Just grab the main body text if specific div is missing
                return soup.get_text(separator=' ', strip=True)[:2000] # Limit to 2000 chars
        return "Could not retrieve details."
    except Exception as e:
        return f"Error: {e}"

def scrape_unicredit_jobs():
    base_url = ""
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
    }
    
    all_jobs = []
    seen_links = set() # NEW: Our memory vault to prevent infinite loops
    
    offset = 0
    page_num = 1
    
    print("[*] Starting extraction engine...\n")
    
    while True:
        current_url = base_url.format(offset)
        print(f"[*] Scraping Page {page_num} (Offset: {offset})...")
        
        try:
            response = httpx.get(current_url, headers=headers, timeout=10.0)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                job_headers = soup.find_all('h3', class_='article__header__text__title')
                
                # We track how many *brand new* jobs we find on this specific page
                new_jobs_on_page = 0
                
                for header in job_headers:
                    link_tag = header.find('a')
                    if link_tag:
                        title = link_tag.text.strip()
                        job_link = link_tag['href']
                        
                        # THE TRAP: Only process it if we haven't seen it before
                        if job_link not in seen_links:
                            seen_links.add(job_link)
                            all_jobs.append({"title": title, "link": job_link})
                            new_jobs_on_page += 1
                
                # THE NEW BREAK CONDITION: 
                # If we found elements, but NONE of them were new jobs, the server is serving junk/ghosts.
                if new_jobs_on_page == 0:
                    print(f"\n[+] No new jobs found. We hit the end of the real database.")
                    break
                    
                print(f"    -> Found {new_jobs_on_page} new jobs.")
                
                offset += 15
                page_num += 1
                time.sleep(1)
                
            else:
                print(f"[-] Access Denied on Page {page_num}. Status Code: {response.status_code}")
                break
                
        except Exception as e:
            print(f"[-] Error making request: {e}")
            break
            
    print(f"\n[SUCCESS] Extraction complete! Total unique jobs collected: {len(all_jobs)}")
    return all_jobs




# --- THE SMART CONTROLLER ---
if __name__ == "__main__":
    # 1. Get the list of 33 jobs
    raw_list = scrape_unicredit_jobs()
    
    if raw_list:
        print(f"\n[*] Total jobs found: {len(raw_list)}")
        print("[*] Filtering for 'Deep Dive' candidates to save money...")
        
        # 2. Define our "Value Keywords"
        # We only spend our 'time' scraping pages that actually look like Data Science roles
        value_keywords = ["data", "analyst", "analysis", "visualization", "statistic", "machine", "intelligence"]
        
        for job in raw_list:
            is_relevant = any(kw in job['title'].lower() for kw in value_keywords)
            
            if is_relevant:
                print(f"    [DEEP DIVE] -> {job['title']}")
                job['description'] = scrape_job_details(job['link'])
                time.sleep(1.5) # Polite delay
            else:
                job['description'] = "Skipped: Not a technical match."

        # 3. Save the enriched data
        with open("unicredit_raw_jobs.json", "w", encoding="utf-8") as f:
            json.dump(raw_list, f, indent=4, ensure_ascii=False)
            
        print("\n[+] SUCCESS: Data enriched with descriptions and saved.")