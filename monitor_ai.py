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

# Secrets
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        requests.post(url, data=data, timeout=10)
    except:
        pass

def get_ai_summary(raw_text):
    if not GROQ_API_KEY:
        return "⚠️ API Key is Missing."

    # Groq API Endpoint (Standard connection, extremely fast)
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    prompt = f"""You are a helpful assistant. Extract job details from the text below.
    If a detail is missing, write "Not Mentioned". 
    Do NOT include Reference Numbers. Keep it short.
    
    RAW TEXT: "{raw_text[:6000]}"
    
    OUTPUT FORMAT:
    *Post:* [Title]
    *Agency:* [Agency Name]
    *Deadline:* [Date]"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # We use Llama 3 (Free and Fast)
    payload = {
        "model": "llama3-8b-8192", 
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"⚠️ Groq Error: {response.status_code}\n{response.text[:100]}"
            
    except Exception as e:
        return f"⚠️ Network Error: {e}"

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
    print("Checking websites (Groq Mode)...")
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
                        time.sleep(1) # Fast sleep because Groq is fast
        except Exception as e:
            print(f"Error: {e}")

    if new_found:
        save_history(seen_jobs)

if __name__ == "__main__":
    check_websites()
