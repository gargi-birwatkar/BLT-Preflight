import requests
from bs4 import BeautifulSoup
from difflib import get_close_matches
import json

class OWASPLiveMapper:
    def __init__(self):
        self.index_url = "https://cheatsheetseries.owasp.org/IndexTopTen.html"
        self.base_url = "https://cheatsheetseries.owasp.org"
        self.mapping = {}
        self.refresh_mapping()

    def refresh_mapping(self):
        """Scrapes the live OWASP index to get the most current cheat sheet list."""
        try:
            response = requests.get(self.index_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links that point to actual cheatsheets
            for link in soup.find_all('a', href=True):
                if 'cheatsheets/' in link['href']:
                    # Clean the name (e.g., "SQL Injection Prevention" -> "SQL Injection")
                    clean_name = link.text.replace(" Cheat Sheet", "").strip()
                    # Ensure the URL is absolute
                    href = link['href']
                    
                    # This ensures there is always exactly one slash
                    full_url = href if href.startswith('http') else f"{self.base_url.rstrip('/')}/{href.lstrip('/')}"
                    self.mapping[clean_name] = full_url
            
            print(f"✅ Successfully mapped {len(self.mapping)} live OWASP Cheat Sheets.")
        except Exception as e:
            print(f"❌ Failed to fetch live index: {e}")
            # Fallback to the Top 10 Index if scraping fails
            self.mapping = {"General": self.index_url}

    def get_best_link(self, ai_category):
        """Uses fuzzy matching to find the most relevant 'Prevention' link."""
        categories = list(self.mapping.keys())
        
        # 1. Try for an exact match (case-insensitive)
        for cat in categories:
            if ai_category.lower() == cat.lower():
                return self.mapping[cat]

        # 2. Try Fuzzy Matching (finds 'Injection' if AI says 'SQL Injection')
        matches = get_close_matches(ai_category, categories, n=1, cutoff=0.4)
        if matches:
            return self.mapping[matches[0]]

        # 3. Smart Keyword Fallback 
        fallbacks = {
        # 1. Broken Authentication / Identity
        "auth": "Authentication_and_Authorization",
        "session": "Session_Management",
        "jwt": "JSON_Web_Token",
        "password": "Authentication_and_Authorization",
        
        # 2. Injection & Data Handling
        "disclosure": "Abuse_Case",      # Fixes the DB Path/Info Disclosure issue
        "leak": "Error_Handling",        # Best for stack trace leaks
        "ssrf": "Server_Side_Request_Forgery",
        "xss": "Cross_Site_Scripting",
        "upload": "File_Upload",         # If someone uploads a malicious script
        
        # 3. Infrastructure & Secrets
        "hardcoded": "DotEnv",           # Direct fix for keys/AWS
        "aws": "Secrets_Management",     # Broader cloud security
        "cloud": "Secrets_Management",
        "random": "Cryptographic_Storage", # If using 'import random' for security
        
        # 4. API & Modern Web
        "api": "REST_Security",
        "graphql": "GraphQL",
        "cors": "Cross-Origin_Resource_Sharing"
    }
        
       # Inside get_best_link:
        for key, target_keyword in fallbacks.items():
            if key in ai_category.lower() or  ai_category.lower() in key:
                # Look for the target_keyword in the keys we scraped from the live site
                for live_key in self.mapping.keys():
                    if target_keyword.lower() in live_key.lower():
                        return self.mapping[live_key]

        # 4. Ultimate Fallback
        return self.index_url

# --- Integration Example ---
if __name__ == "__main__":
    mapper = OWASPLiveMapper()
    
    test_categories = ["SQL Injection", "Information Disclosure", "Hardcoded AWS Key"]
    
    print("\n--- Testing Live Mapping ---")
    for test in test_categories:
        link = mapper.get_best_link(test)
        print(f"🔍 AI Found: {test}")
        print(f"🔗 Linked to: {link}\n")