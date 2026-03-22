import json

def reset_companies_config(target_company="Holidu"):
    """Resets all companies to inactive, except for the specified target."""
    filepath = "config/companies.json"
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            companies = json.load(f)
            
        for company in companies:
            if company["name"] == target_company:
                company["is_active"] = True
            else:
                company["is_active"] = False
                
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(companies, f, indent=4)
            
        print(f"[+] Successfully updated {filepath}.")
        print(f"    -> All scrapers disabled EXCEPT: {target_company}")
        
    except FileNotFoundError:
        print(f"[-] Error: Could not find {filepath}. Make sure you are in the right directory.")

if __name__ == "__main__":
    reset_companies_config()