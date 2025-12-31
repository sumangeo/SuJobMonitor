import requests
from bs4 import BeautifulSoup
import os
import google.generativeai as genai
import time

# --- CONFIGURATION ---
URLS = [
    "https://www.bppa.gov.bd/advertisement-notices/advertisement-services.html",
    "https://bdjobs.com"
]

# Keywords to find
KEYWORDS = ["Individual Consultant", "SIC", "Consultant", "National Consultant", "Individual Local Consultant", "Local Consultant", "Environment", "Environmental", "Natural", "Disaster", "Water", "Expert", "Monitoring", "Evaluation", "Specialist"]


# File to remember sent jobs (prevents repetition)
HISTORY_FILE = "history.txt"

# --- SECRETS FROM GITHUB ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Setup AI
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    # disable_web_page_preview=True makes the chat cleaner
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram Error: {e}")

def summarize_with_ai(raw_text):
    """
    Uses Gemini to clean up the text.
    """
    if not GEMINI_API_KEY:
        return raw_text # Fallback if no key
        
    prompt = f"""
    Analyze this raw text from a Bangladesh government job circular list.
    Extract the following details. If a detail is missing, write "Not Mentioned".
    Keep it very short.
    
    Raw Text: "{raw_text}"
    
    Format:
    *Title:* [Insert Title]
    *Agency:* [Insert Ministry/Department Name]
    *Method:* [e.g. SIC / Local Consultant]
    *Education:* [Insert Academic Qualification]
    *Experience:* [Insert required year of experience]
    *Deadline:* [Insert Date if found]
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return raw_text # Fallback if AI fails

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

    for url in URLS:
        try:
            response = requests.get(url, headers=headers, timeout=20)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Get all table rows
            rows = soup.find_all('tr')

            for row in rows:
                text = row.get_text(" ", strip=True)
                
                # Check if it matches keywords and is long enough to be real content
                if any(k.lower() in text.lower() for k in KEYWORDS) and len(text) > 25:
                    
                    # Create unique ID based on the text content
                    job_id = str(hash(text))
                    
                    if job_id not in seen_jobs:
                        seen_jobs.add(job_id)
                        new_found = True
                        
                        # Summarize with AI
                        clean_summary = summarize_with_ai(text)
                        
                        # Send Message
                        msg = f"🔔 **Suman Sir, New Job Detected!**\n\n{clean_summary}\n\n🔗 [View Source]({url})"
                        send_telegram(msg)
                        
                        # Wait 2 seconds to be polite to the AI server
                        time.sleep(2)

        except Exception as e:
            print(f"Error on {url}: {e}")

    # Save history if we found something new
    if new_found:
        save_history(seen_jobs)
        print("History updated.")

if __name__ == "__main__":
    check_websites()
