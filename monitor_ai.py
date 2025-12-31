import requests
from bs4 import BeautifulSoup
import os
import google.generativeai as genai
import time
import urllib.parse

# --- CONFIGURATION ---
URLS = [
    "https://www.bppa.gov.bd/advertisement-notices/advertisement-services.html",
    "https://bdjobs.com"
]

KEYWORDS = ["Individual Consultant", "SIC", "Consultant", "National Consultant", "Individual Local Consultant", "Local Consultant", "Environment", "Environmental", "Natural", "Disaster", "Water", "Expert", "Monitoring", "Evaluation", "Specialist"]
HISTORY_FILE = "history.txt"

# --- SECRETS ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- SMART MODEL SETUP ---
def get_ai_response(prompt):
    """
    Tries to use Gemini Flash. If it fails (due to old library), 
    it automatically switches to Gemini Pro.
    """
    if not GEMINI_API_KEY:
        return "⚠️ API Key Missing."

    genai.configure(api_key=GEMINI_API_KEY)

    # 1. Try the Fast/New Model First
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Flash failed ({e}), switching to Backup Model...")
        
    # 2. Fallback to the 'Classic' Model (Works on old libraries)
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ AI Error: {str(e)[:100]}"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram Error: {e}")

def get_page_content(link):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(link, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        # Remove junk script tags
        for script in soup(["script", "style", "header", "footer", "nav"]):
            script.decompose()
        return soup.get_text(" ", strip=True)
    except:
        return None

def summarize_details(raw_text, link):
    prompt = f"""
    Extract job details from this text. Keep it short.
    If missing, write "Not Mentioned". Do NOT include Ref No.
    
    RAW TEXT: "{raw_text[:4000]}" 
    
    OUTPUT FORMAT:
    *Post:* [Title Of Service]
    *Agency:* [Name of Ministry/Department, Agency]
    *Project:* [Name of Project/Programme]
    *Education:* [Brief degree requirement, e.g., Masters in Environmental Science]
    *Experience:* [Years of experience required]
    *Salary:* [Mention salary if found, otherwise 'Negotiable']
    *Deadline:* [Date]
    """
    return get_ai_response(prompt)

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
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

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
                        print(f"New Job: {full_link}")
                        seen_jobs.add(job_id)
                        new_found = True
                        
                        # Get Details & Summarize
                        detail_text = get_page_content(full_link)
                        if detail_text:
                            summary = summarize_details(detail_text, full_link)
                            msg = f"🔔 **New Circular Detected!**\n\n{summary}\n\n🔗 [View Details]({full_link})"
                            send_telegram(msg)
                            
                        time.sleep(5) # Slow down to prevent errors

        except Exception as e:
            print(f"Error checking {base_url}: {e}")

    if new_found:
        save_history(seen_jobs)

if __name__ == "__main__":
    check_websites()
