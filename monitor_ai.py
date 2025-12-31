import requests
from bs4 import BeautifulSoup
import os
import time
import urllib.parse
import json

# --- CONFIGURATION ---
URLS = [
    "https://www.bppa.gov.bd/advertisement-notices/advertisement-services.html",
    "https://lged.gov.bd/site/view/notices",
    "https://www.rhd.gov.bd/PublicProcurement/Index.asp"
]
KEYWORDS = ["Individual Consultant", "SIC", "REOI", "National Consultant", "Environmental", "Specialist"]
HISTORY_FILE = "history.txt"
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# List of models to try (The script will try them in order)
MODELS_TO_TRY = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash-001",
    "gemini-1.5-pro",
    "gemini-1.0-pro",
    "gemini-pro"
]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        requests.post(url, data=data, timeout=10)
    except:
        pass

def get_ai_summary(raw_text):
    if not GEMINI_API_KEY:
        return "⚠️ API Key is Missing."

    prompt = f"""Extract job details. Write 'Not Mentioned' if missing. Do NOT include Ref No.
    RAW TEXT: "{raw_text[:4000]}"
    OUTPUT FORMAT:
    *Post:* [Title]
    *Agency:* [Agency Name]
    *Deadline:* [Date]"""

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {'Content-Type': 'application/json'}

    # --- BRUTE FORCE LOOP ---
    # We try every model in the list until one works
    for model_name in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        
        try:
            # print(f"Trying model: {model_name}...") # Debug
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
            
            if response.status_code == 200:
                # SUCCESS! We found a working model.
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429:
                return "⚠️ AI Busy (Rate Limit)."
            elif response.status_code == 400 and "API_KEY" in response.text:
                 return "⚠️ API Key Invalid."
            # If 404, we just continue to the next model in the list...
            
        except Exception as e:
            pass # Network error, try next model
            
    # If we finish the loop and NOTHING worked:
    return "⚠️ AI Failed. All models returned 404. Check your API Key permissions."

def get_page_content(link):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(link, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        for s in soup(["script", "style"]): s.decompose()
        return soup.get_text(" ", strip=True)
    except: return None

def load_history():
    if not os.path.exists(HISTORY_FILE): return set()
    with open(HISTORY_FILE, "r") as f: return set(line.strip() for line in f)

def save_history(seen_set):
    with open(HISTORY_FILE, "w") as f:
        for item in seen_set: f.write(f"{item}\n")

def check_websites():
    print("Checking websites...")
    seen_jobs = load_history()
    new_found = False
    headers = {'User-Agent': 'Mozilla/5.0'}

    for base_url in URLS:
        try:
            response = requests.get(base_url, headers=headers, timeout=20)
            soup = BeautifulSoup(response.content, 'html.parser')
            rows = soup.find_all('tr')

            for row in rows:
                row_text = row.get_text(" ", strip=True)
                if any(k.lower() in row_text.lower() for k in KEYWORDS) and len(row_text) > 25:
                    link_tag = row.find('a', href=True)
                    if not link_tag: continue
                    
                    full_link = urllib.parse.urljoin(base_url, link_tag['href'])
                    job_id = str(hash(full_link))
                    
                    if job_id not in seen_jobs:
                        seen_jobs.add(job_id)
                        new_found = True
                        
                        detail_text = get_page_content(full_link)
                        if detail_text:
                            summary = get_ai_summary(detail_text)
                            msg = f"🔔 **New Circular Detected!**\n\n{summary}\n\n🔗 [View Details]({full_link})"
                            send_telegram(msg)
                        time.sleep(2)
        except Exception as e:
            print(f"Error: {e}")

    if new_found:
        save_history(seen_jobs)

if __name__ == "__main__":
    check_websites()
