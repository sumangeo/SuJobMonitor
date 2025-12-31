import requests
from bs4 import BeautifulSoup
import os

# --- CONFIGURATION ---
URLS = [
    "https://www.bppa.gov.bd/advertisement-notices/advertisement-services.html", 
    "https://lged.gov.bd/site/view/notices",
    "https://www.rhd.gov.bd/PublicProcurement/Index.asp"
]
KEYWORDS = ["Individual Consultant", "SIC", "Consultant", "National Consultant", "Individual Local Consultant", "Local Consultant", "Environment", "Environmental", "Natural", "Disaster", "Water", "Expert", "Monitoring", "Evaluation", "Specialist"]

# Get these from Environment Variables (for security)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram_alert(message):
    send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(send_url, data=data)
    except Exception as e:
        print(f"Error sending Telegram: {e}")

def check_websites():
    print("Checking websites...")
    found_new = False
    
    for url in URLS:
        try:
            # Fake browser header is crucial for cloud servers
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=20)
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text()
            
            # Simple check logic
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            for line in lines:
                if any(k.lower() in line.lower() for k in KEYWORDS) and len(line) > 20:
                    # Found a match!
                    msg = f"🔔 **New Circular Found!**\n\nSource: {url}\n\nText: {line[:100]}..."
                    send_telegram_alert(msg)
                    found_new = True
                    break # Stop checking this site if we found one match to avoid spam
                    
        except Exception as e:
            print(f"Failed to check {url}: {e}")

if __name__ == "__main__":

    check_websites()
