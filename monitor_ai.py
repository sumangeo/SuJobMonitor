import requests
from bs4 import BeautifulSoup
import os
import time
import urllib.parse

# --- CONFIGURATION ---
URLS = [
    "https://www.bppa.gov.bd/advertisement-notices/advertisement-services.html",
    "https://lged.gov.bd/site/view/notices",
    "https://www.rhd.gov.bd/PublicProcurement/Index.asp"
]
KEYWORDS = ["Individual Consultant", "SIC", "REOI", "National Consultant", "Environmental", "Specialist"]
HISTORY_FILE = "history.txt"

# Secrets (Only Telegram needed now)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        requests.post(url, data=data, timeout=10)
    except:
        pass

def load_history():
    if not os.path.exists(HISTORY_FILE): return set()
    with open(HISTORY_FILE, "r") as f: return set(line.strip() for line in f)

def save_history(seen_set):
    with open(HISTORY_FILE, "w") as f:
        for item in seen_set: f.write(f"{item}\n")

def check_websites():
    print("Checking websites (Direct Mode - No Keys)...")
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
                        
                        # --- DIRECT EXTRACTION (No AI) ---
                        # We grab the title directly from the link text
                        title = link_tag.get_text(" ", strip=True)
                        
                        # We try to find a date in the row text
                        import re
                        date_match = re.search(r'\d{2}/\d{2}/\d{4}', row_text)
                        deadline = date_match.group(0) if date_match else "See Details"

                        msg = (
                            f"🔔 **New Circular Detected!**\n\n"
                            f"📌 *Post:* {title}\n"
                            f"📅 *Deadline:* {deadline}\n\n"
                            f"🔗 [View Details]({full_link})"
                        )
                        send_telegram(msg)
                        time.sleep(1)

        except Exception as e:
            print(f"Error: {e}")

    if new_found:
        save_history(seen_jobs)

if __name__ == "__main__":
    check_websites()
