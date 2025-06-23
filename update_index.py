import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json
import os

# ---- Settings ----
INDEX_FILE = "index.html"
LAST_SEEN_FILE = "last_law.txt"
FEED_URL = "https://www.legislation.gov.uk/uksi/data.feed"
DATE_DISPLAY = datetime.today().strftime("%-d %B %Y")
OPENROUTER_API_KEY = "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"
MODEL_NAME = "deepseek/deepseek-chat-v3-0324:free"

# ---- Step 1: Fetch feed ----
print("Fetching UK legislation feed...")
r = requests.get(FEED_URL)
soup = BeautifulSoup(r.content, "lxml-xml")
entries = soup.find_all("entry")

if not entries:
    print("No entries found.")
    exit()

# ---- Step 2: Load last seen law ID or create on first run ----
last_seen_id = None
if os.path.exists(LAST_SEEN_FILE):
    with open(LAST_SEEN_FILE, "r") as f:
        last_seen_id = f.read().strip()
else:
    first_id = entries[0].id.text.strip()
    with open(LAST_SEEN_FILE, "w") as f:
        f.write(first_id)
    print("Initialisation complete. Will begin logging new laws from next run.")
    exit()

# ---- Step 3: Filter new laws since last seen ----
new_entries = []
for entry in entries:
    entry_id = entry.id.text.strip()
    if entry_id == last_seen_id:
        break
    new_entries.append(entry)

if not new_entries:
    print("No new laws to process.")
    exit()

print(f"Processing {len(new_entries)} new law(s)...")

# ---- Step 4: Process new laws (oldest first) ----
for entry in reversed(new_entries):
    title = entry.title.text.strip()
    link = entry.id.text.strip()
    print(f"Processing: {title}")

    match = re.search(r"https?://www\.legislation\.gov\.uk/(?:id/)?uksi/(\d{4}/\d+)", link)
    if not match:
        print("Skipping – could not extract SI number.")
        continue

    si_path = match.group(1)
    note_url = f"https://www.legislation.gov.uk/uksi/{si_path}/note/made"
    print(f"Fetching explanatory note: {note_url}")

    try:
        note_response = requests.get(note_url)
        note_soup = BeautifulSoup(note_response.content, "html.parser")
        paras = note_soup.find_all("p", class_="LegExpNoteText")
        all_text = " ".join(p.text.strip() for p in paras if p.text.strip())

        if not all_text:
            summary_text = "No explanatory summary available."
        else:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://chat.openai.com/",
                "X-Title": "AngloLawLedger"
            }

            prompt = (
                "Summarise the following UK legislation explanatory note in one paragraph. "
                "Use a plainspoken, human tone suitable for the public. Do not include any introductions like "
                "'Here is a summary' and do not include word counts or metadata. Just return the plain summary.\n\n"
                f"{all_text}"
            )

            data = {
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": "You simplify official UK legal explanatory notes for the public."},
                    {"role": "user", "content": prompt}
                ]
            }

            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, data=json.dumps(data))
            response.raise_for_status()
            ai_result = response.json()
            summary_text = ai_result["choices"][0]["message"]["content"].strip()

    except Exception as e:
        summary_text = "No explanatory summary available."

    # ---- Step 5: Insert into HTML ----
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    insertion_marker = "<!-- Law entries will be inserted here by the Python script -->"
    insertion_point = html.find(insertion_marker)
    if insertion_point != -1:
        insertion_point += len(insertion_marker)
    else:
        insertion_marker = "</main>"
        insertion_point = html.find(insertion_marker)
        if insertion_point == -1:
            print("Error: Could not find insertion point.")
            continue

    entry_html = f"""
    <div class="law-entry">
      <h2>{DATE_DISPLAY}</h2>
      <p><strong>Law:</strong> {title}</p>
      <p>{summary_text}</p>
      <p><a href="{link}">View full legislation</a></p>
    </div>
    """

    html = html[:insertion_point] + entry_html + html[insertion_point:]

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print("Law added to homepage.")

# ---- Step 6: Update last seen law ID ----
latest_id = entries[0].id.text.strip()
with open(LAST_SEEN_FILE, "w") as f:
    f.write(latest_id)

print("Updated last_law.txt. Script complete.")
