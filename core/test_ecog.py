import httpx
from bs4 import BeautifulSoup

def test_ecog_recon():
    url = "https://ecog.jobs.personio.de/?language=en"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    print("[*] Fetching EcoG Personio board...")
    response = httpx.get(url, headers=headers)
    
    # Parse the raw HTML into a searchable tree
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find ALL anchor tags (links) on the entire page
    all_links = soup.find_all('a')
    
    print(f"[*] Found {len(all_links)} total links. Scanning for job patterns...\n")
    print("="*50)
    
    for link in all_links:
        href = link.get('href')
        text = link.get_text(strip=True)
        classes = link.get('class', [])
        
        # We only care about links that actually have text and an href
        if href and text:
            print(f"TEXT: {text}")
            print(f"HREF: {href}")
            print(f"CSS CLASSES: {classes}")
            print("-" * 50)

if __name__ == "__main__":
    test_ecog_recon()