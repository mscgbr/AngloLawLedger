import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ---- Settings ----
INDEX_FILE = "index.html"
FEED_URL = "https://www.legislation.gov.uk/uksi/data.feed"
DATE_DISPLAY = datetime.today().strftime("%-d %B %Y")

# ---- Step 1: Fetch feed ----
print("Fetching latest UK law from official feed...")
r = requests.get(FEED_URL)
soup = BeautifulSoup(r.content, "xml")

entries = soup.find_all("entry")
if not entries:
    print("No laws found in feed.")
    exit()

# ---- Step 2: Get most recent law ----
first = entries[0]
title = first.title.text.strip()
link = first.id.text.strip()

print(f"Found: {title}")

# ---- Step 3: Load index.html ----
with open(INDEX_FILE, "r", encoding="utf-8") as f:
    html = f.read()

insertion_point = html.find("</body>")
if insertion_point == -1:
    print("Could not find </body> in HTML.")
    exit()

# ---- Step 4: Insert new entry block ----
entry_html = f"""
  <div class="entry">
    <h2>{DATE_DISPLAY}</h2>
    <p><strong>Law:</strong> {title}</p>
    <p><a href="{link}">View on legislation.gov.uk</a></p>
  </div>
"""

html = html[:insertion_point] + entry_html + html[insertion_point:]

# ---- Step 5: Save result ----
with open(INDEX_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print("✅ Law entry added to homepage.")
