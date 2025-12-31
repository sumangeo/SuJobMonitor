import requests
from bs4 import BeautifulSoup
import os
import time
import urllib.parse
import re

# --- CONFIGURATION ---
URLS = [
    "https://www.bppa.gov.bd/advertisement-notices/advertisement-services.html",
    "https://bdjobs.com"
]
KEYWORDS = ["Individual Consultant", "SIC", "Consultant", "National Consultant", "Individual Local Consultant", "Local Consultant", "Environment", "Environmental", "Natural", "Disaster", "Water", "Expert", "Monitoring", "Evaluation", "Specialist"]
HISTORY_FILE = "history.txt"

# Secrets
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        requests.post(url, data=data, timeout=10)
    except:
        pass

def get_page_details(link):
    """
    Visits the detail page and hunts for specific info using text patterns.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(link, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text(" ", strip=True)

        # Defaults
        project = "Not Mentioned"
        education = "Not Mentioned"
        experience = "Not Mentioned"
        salary = "Negotiable"

        # --- 1. FIND PROJECT NAME ---
        # Look for "Project Name" followed by text
        proj_match = re.search(r'Project.*?Name\s*[:\-]?\s*([A-Za-z0-9\s\(\)\-]+)', text, re.IGNORECASE)
        if proj_match:
            project = proj_match.group(1)[:60] + "..." # Limit length

        # --- 2. FIND EDUCATION ---
        # Look for degrees like Master, Bachelor, PhD
        edu_keywords = ["Master", "Bachelor", "Degree", "PhD", "Diploma", "B.Sc", "M.Sc"]
        for keyword in edu_keywords:
            if keyword in text:
                # Try to grab the sentence containing the degree
                edu_match = re.search(r'([^.]*' + keyword + r'[^.]*)', text)
                if edu_match:
                    education = edu_match.group(1).strip()[:80] # Grab first 80 chars
                    break
        
        # --- 3. FIND EXPERIENCE ---
        # Look for "X Years"
        exp_match = re.search(r'(\d+|One|Two|Three|Four|Five|Ten|Fifteen)\s*(\(\w+\))?\s*Yea?rs', text, re.IGNORECASE)
        if exp_match:
            experience = exp_match.group(0) # e.g., "15 Years"

        # --- 4. FIND SALARY ---
        # Look for "Salary", "Remuneration", "BDT", "Tk"
        sal_match = re.search(r'(Salary|Remuneration|Monthly).*?(\d{4,})', text, re.IGNORECASE)
        if sal_match:
            salary = f"{sal_match.group(2)} BDT"

        return project, education, experience, salary

    except Exception as e:
        print(f"Error reading details: {e}")
        return "Error", "Error", "Error", "Error"

def load_history():
    if not os.path.exists(HISTORY_FILE): return set()
    with open(HISTORY_FILE, "r") as f: return set(line.strip() for line in f)

def save_history(seen_set):
    with open(HISTORY_FILE, "w") as f:
        for item in seen_set: f.write(f"{item}\n")

def check_websites():
    print("Checking websites (Deep Scraper Mode)...")
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
                        
                        # --- 1. Basic Info from Table ---
                        raw_title = link_tag.get_text(" ", strip=True)
                        clean_title = re.split(r'Ref\s*\.?\s*No', raw_title, flags=re.IGNORECASE)[0]
                        clean_title = re.sub(r'\d{2,}\.\d{2,}\.\d+', '', clean_title).strip(" -:,")
                        
                        # Agency is often in the 3rd column
                        cols = row.find_all('td')
                        agency = cols[2].get_text(" ", strip=True)[:40] if len(cols) > 2 else "Govt Agency"
                        
                        # Deadline
                        date_match = re.search(r'\d{2}/\d{2}/\d{4}', row_text)
                        deadline = date_match.group(0) if date_match else "See Details"

                        # --- 2. DEEP DIVE: Fetch Details from Link ---
                        print(f"Fetching details for: {clean_title}...")
                        project, education, experience, salary = get_page_details(full_link)

                        # --- 3. Send Message ---
                        msg = (
                            f"🔔 **New Circular Detected!**\n\n"
                            f"📌 *Post:* [{clean_title}]({full_link})\n"
                            f"🏢 *Agency:* {agency}\n"
                            f"🏗️ *Project:* {project}\n"
                            f"🎓 *Education:* {education}\n"
                            f"⏳ *Experience:* {experience}\n"
                            f"💰 *Salary:* {salary}\n"
                            f"📅 *Deadline:* {deadline}"
                        )
                        send_telegram(msg)
                        time.sleep(2) # Wait 2s between pages to be polite

        except Exception as e:
            print(f"Error: {e}")

    if new_found:
        save_history(seen_jobs)

if __name__ == "__main__":
    check_websites()
