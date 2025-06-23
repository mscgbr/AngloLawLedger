import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

# ---- Settings ----
INDEX_FILE = "index.html"
FEED_URL = "https://www.legislation.gov.uk/uksi/data.feed"
DATE_DISPLAY = datetime.today().strftime("%-d %B %Y")

# ---- Step 1: Fetch feed ----
print("Fetching latest UK law from official feed...")
r = requests.get(FEED_URL)
soup = BeautifulSoup(r.content, "lxml-xml")

entries = soup.find_all("entry")
if not entries:
    print("No laws found in feed.")
    exit()

# ---- Step 2: Get most recent law ----
first = entries[0]
title = first.title.text.strip()
link = first.id.text.strip()
print(f"Found: {title}")

# ---- Step 3: Construct explanatory note URL ----
match = re.search(r"https?://www\.legislation\.gov\.uk/(?:id/)?uksi/(\d{4}/\d+)", link)
if not match:
    print("Could not extract SI number from link.")
    summary_text = "No explanatory summary available."
else:
    si_path = match.group(1)
    note_url = f"https://www.legislation.gov.uk/uksi/{si_path}/note/made"
    print(f"Fetching explanatory note: {note_url}")

    try:
        note_response = requests.get(note_url)
        note_soup = BeautifulSoup(note_response.content, "html.parser")

        # Get all explanatory paragraphs
        paras = note_soup.find_all("p", class_="LegExpNoteText")
        summary_blocks = []

        for p in paras:
            clean = p.text.strip()
            if clean:
                summary_blocks.append(f"<p>{clean}</p>")

        if summary_blocks:
            summary_text = "\n".join(summary_blocks)
        else:
            summary_text = "No explanatory summary could be extracted."

    except Exception as e:
        summary_text = f"Could not fetch explanatory note. Error: {e}"

# ---- Step 4: Load index.html ----
with open(INDEX_FILE, "r", encoding="utf-8") as f:
    html = f.read()

# Try to find insertion marker
insertion_marker = "<!-- Law entries will be inserted here by the Python script -->"
insertion_point = html.find(insertion_marker)
if insertion_point != -1:
    insertion_point += len(insertion_marker)
else:
    # Fallback: insert before </main>
    print("Warning: Marker not found, falling back to inserting before </main>")
    insertion_marker = "</main>"
    insertion_point = html.find(insertion_marker)
    if insertion_point == -1:
        print("Error: Could not find fallback insertion point.")
        exit()

# ---- Step 5: Insert new entry block ----
entry_html = f"""
    <div class="law-entry">
      <h2>{DATE_DISPLAY}</h2>
      <p><strong>Law:</strong> {title}</p>
      {summary_text}
      <p><a href="{link}">View full legislation</a></p>
    </div>
"""

print("\n--- Entry to be inserted ---\n")
print(entry_html)

html = html[:insertion_point] + entry_html + html[insertion_point:]

# ---- Step 6: Save result ----
with open(INDEX_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\nLaw entry added and written to: {INDEX_FILE}")
