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

# Keywords to match in the Title first
KEYWORDS = ["Individual Consultant", "SIC", "Consultant", "National Consultant", "Individual Local Consultant", "Local Consultant", "Environment", "Environmental", "Natural", "Disaster", "Water", "Expert", "Monitoring", "Evaluation", "Specialist"]

HISTORY_FILE = "history.txt"

# --- SECRETS ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # --- SETUP AI MODEL ---
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Try the newest model first, but have a backup plan
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
        except:
            print("⚠️ Flash model failed, switching to backup...")
            model = genai.GenerativeModel('gemini-pro')

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram Error: {e}")

def get_page_content(link):
    """
    Follows the link to get the full detailed text.
    """
    try:
        # Fake a browser visit to avoid blocking
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(link, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get text from the body, removing script/style tags
        for script in soup(["script", "style", "header", "footer", "nav"]):
            script.decompose()
            
        return soup.get_text(" ", strip=True)
    except Exception as e:
        print(f"Could not fetch details: {e}")
        return None

def summarize_full_details(raw_text, link):
    if not GEMINI_API_KEY:
        return f"⚠️ API Key Missing in Secrets. [View Link]({link})"
        
    prompt = f"""
    You are a helpful assistant. Extract job details from this text.
    If a detail is missing, write "Not Mentioned".
    Do NOT include Reference Numbers.
    
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
    
    try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"!!! AI ERROR !!!: {e}")
            # If the specific model failed during generation, try the backup one last time
            try:
                backup_model = genai.GenerativeModel('gemini-pro')
                response = backup_model.generate_content(prompt)
                return response.text
            except:
                return f"⚠️ AI Failed. [View Link]({link})"

def load_history():
    if not os.path.exists(HISTORY_FILE): return set()
    with open(HISTORY_FILE, "r") as f: return set(line.strip() for line in f)

def save_history(seen_set):
    with open(HISTORY_FILE, "w") as f:
        for item in seen_set: f.write(f"{item}\n")

def check_websites():
    print("Checking websites with Detail Extraction...")
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
                
                # 1. First Check: Is this a relevant job?
                if any(k.lower() in row_text.lower() for k in KEYWORDS) and len(row_text) > 25:
                    
                    # 2. Extract the Link (The key change!)
                    link_tag = row.find('a', href=True)
                    if not link_tag:
                        continue
                        
                    relative_link = link_tag['href']
                    # Convert "details.html" to "https://bppa.gov.bd/details.html"
                    full_link = urllib.parse.urljoin(base_url, relative_link)
                    
                    # Unique ID based on the link (more accurate than text)
                    job_id = str(hash(full_link))
                    
                    if job_id not in seen_jobs:
                        print(f"New Job Found: {full_link}")
                        seen_jobs.add(job_id)
                        new_found = True
                        
                        # 3. Go to that page and get full details
                        detail_text = get_page_content(full_link)
                        
                        if detail_text:
                            # 4. Summarize the FULL details
                            ai_summary = summarize_full_details(detail_text, full_link)
                            
                            msg = f"🔔 **New Circular Detected!**\n\n{ai_summary}\n\n🔗 [Apply / View Details]({full_link})"
                            send_telegram(msg)
                            
                        # Sleep to be polite to the server
                        time.sleep(3)

        except Exception as e:
            print(f"Error on {base_url}: {e}")

    if new_found:
        save_history(seen_jobs)
        print("History updated.")

if __name__ == "__main__":
    check_websites()



