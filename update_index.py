import os
import requests
import feedparser
from datetime import datetime
from bs4 import BeautifulSoup
import re

FEED_URL = "https://www.legislation.gov.uk/uksi/latest?dataType=xml"
INDEX_HTML = "index.html"
LAST_LAW_FILE = "last_law.txt"

def fetch_feed():
    print("Fetching UK legislation feed...")
    return feedparser.parse(FEED_URL)

def extract_si_number(entry_title):
    match = re.search(r"\b(\d{4})/(\d+)\b", entry_title)
    if match:
        return int(match.group(2))
    return None

def get_last_processed_si():
    if os.path.exists(LAST_LAW_FILE):
        with open(LAST_LAW_FILE, "r") as f:
            return int(f.read().strip())
    return 0

def set_last_processed_si(si_number):
    with open(LAST_LAW_FILE, "w") as f:
        f.write(str(si_number))

def extract_explanatory_note_text(url):
    print(f"Fetching explanatory note: {url}")
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        text_element = soup.find("div", {"id": "content"})
        if text_element:
            text = text_element.get_text(strip=True)
            return text
    except Exception as e:
        print(f"Error fetching explanatory note: {e}")
    return ""

def summarise_explanatory_note(text):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    print(f"OPENROUTER_API_KEY present in environment: {api_key is not None}")
    print(f"API_KEY length: {len(api_key) if api_key else 'None'}")

    if not api_key:
        print("No API key provided.")
        return "No explanatory summary available."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "mistral",
        "messages": [
            {"role": "system", "content": "Summarise the explanatory note in one plainspoken paragraph for non-lawyers."},
            {"role": "user", "content": text}
        ]
    }

    try:
        print("Calling OpenRouter API...")
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        print(f"API status: {response.status_code}")
        print(f"API response: {response.text[:200]}")
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Error during API call: {e}")
        return "No explanatory summary available."

def update_index(new_entry):
    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        content = f.read()

    insertion = "<!-- NEW LAW ENTRY -->"
    if insertion not in content:
        print("ERROR: Insertion point not found in index.html.")
        return

    updated = content.replace(insertion, new_entry + "\n\n" + insertion)
    with open(INDEX_HTML, "w", encoding="utf-8") as f:
        f.write(updated)

def main():
    feed = fetch_feed()
    last_si = get_last_processed_si()
    print(f"Last processed SI number: {last_si}")
    processed = 0

    for entry in feed.entries:
        title = entry.title
        link = entry.link
        si_number = extract_si_number(title)

        print(f"Processing: {title}")

        if si_number is None:
            print("Skipping – could not extract SI number.")
            continue
        if si_number <= last_si:
            continue

        note_url = link + "/note/made"
        note_text = extract_explanatory_note_text(note_url)
        summary = summarise_explanatory_note(note_text)

        if note_text.strip():
            print("Extracted explanatory note (first 300 chars):", note_text[:300])
        else:
            print("No explanatory note text found.")

        date_str = datetime.today().strftime("%-d %B %Y")
        new_entry = f"""
        <div class="law-entry">
            <h3>{title}</h3>
            <p><strong>Date Added:</strong> {date_str}</p>
            <p><strong>Explanatory Summary:</strong> {summary}</p>
            <p><a href="{link}" target="_blank">View Full Legislation</a></p>
        </div>
        """

        update_index(new_entry)
        set_last_processed_si(si_number)
        print("Law added to homepage.")
        processed += 1

        if processed >= 20:
            break

    print("Updated last_law.txt. Script complete.")

if __name__ == "__main__":
    main()
