import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import json
import re

# --- Settings ---
FEED_URL = "https://www.legislation.gov.uk/uksi/data.feed"
COUNTRY = "uk"
BASE_DIR = f"laws/{COUNTRY}"
LATEST_GLOBAL = "laws/latest.json"
MODEL_NAME = "qwen/qwen3-235b-a22b:free"

# --- Ensure folders exist ---
os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs("laws", exist_ok=True)

# --- API Key ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    print("Error: OPENROUTER_API_KEY not found.")
    exit(1)

# --- Load feed ---
r = requests.get(FEED_URL)
soup = BeautifulSoup(r.content, "lxml-xml")
entries = soup.find_all("entry")
if not entries:
    print("No entries found.")
    exit()

# --- Load existing titles ---
def collect_existing_titles(base_dir="laws"):
    titles = set()
    for dirpath, _, filenames in os.walk(base_dir):
        for filename in filenames:
            if filename.endswith(".json"):
                filepath = os.path.join(dirpath, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for item in data:
                                if "title" in item:
                                    titles.add(item["title"].strip())
                except Exception:
                    continue
    return titles

existing_titles = collect_existing_titles()

# --- Robust JSON loader ---
def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Failed to parse {path}. Returning empty list.")
                return []
    return []

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# --- Load global latest list ---
latest_global = load_json(LATEST_GLOBAL)

# --- Process entries ---
for entry in reversed(entries):
    title = entry.title.text.strip()
    if title in existing_titles:
        continue  # Skip duplicate

    link = entry.id.text.strip()
    law_date = datetime.utcnow().strftime("%-d %B %Y")
    year = datetime.utcnow().strftime("%Y")

    match = re.search(r"/uksi/(\d{4}/\d+)", link)
    if not match:
        continue

    si_path = match.group(1)
    note_url = f"https://www.legislation.gov.uk/uksi/{si_path}/note/made"

    try:
        note_response = requests.get(note_url)
        soup = BeautifulSoup(note_response.content, "html.parser")
        paras = soup.find_all("p", class_="LegExpNoteText")
        raw_text = " ".join(p.text.strip() for p in paras if p.text.strip())

        if not raw_text:
            summary = "No explanatory summary available."
        else:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://chat.openai.com/",
                "X-Title": "AngloLawLedger"
            }
            prompt = (
                "Rewrite the following explanatory note from UK legislation into one short, clear paragraph. "
                "Use plain English. Focus on real-world impact—what the law changes, what that allows, and how it might affect people, services, or systems. "
                "Be direct, no disclaimers or legalese. Highlight any concrete outcomes where possible. "
                "Wrap the final summary ONLY between the ##SUMMARY_START and ##SUMMARY_END markers:\n\n" + raw_text
            )

            payload = {
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": (
                        "You are an expert at rewriting UK legal explanatory notes into short, impactful public summaries. "
                        "Focus on what’s changing and what it enables. Use plain English, avoid legal jargon, and explain the real-world significance—whether for public services, oversight, businesses, the environment, or vulnerable groups. "
                        "Never hedge or explain what the law won’t do. Your tone is confident, clear, and free of fluff."
                    )},
                    {"role": "user", "content": prompt}
                ]
            }
            ai_resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, data=json.dumps(payload))
            full_output = ai_resp.json()["choices"][0]["message"]["content"].strip()

            # Extract only the final summary between markers
            summary_match = re.search(r"##SUMMARY_START\s*(.*?)\s*##SUMMARY_END", full_output, re.DOTALL)
            if summary_match:
                summary = summary_match.group(1).strip()
            else:
                print("Warning: AI response did not contain valid summary markers. Saving full output.")
                summary = full_output

    except Exception as e:
        print(f"Summary failed: {e}")
        summary = "No explanatory summary available."

    law_entry = {
        "date": law_date,
        "title": title,
        "link": link,
        "summary": summary,
        "country": "United Kingdom"
    }

    # --- Append to year file ---
    year_file = f"{BASE_DIR}/{year}.json"
    year_data = load_json(year_file)
    year_data.insert(0, law_entry)
    save_json(year_file, year_data)

    # --- Update global latest list (capped to 50) ---
    latest_global.insert(0, law_entry)
    latest_global = latest_global[:50]

    print(f"Added: {title}")

# --- Save global list ---
save_json(LATEST_GLOBAL, latest_global)

print("Done.")
