# inspect_fbise.py
import requests
from bs4 import BeautifulSoup

url = "https://fbisepastpapers.com/class-9-fbise-past-papers/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

resp = requests.get(url, headers=headers)
print(f"Status: {resp.status_code}")

# Save HTML to file for inspection
with open("fbise_class9_debug.html", "w", encoding="utf-8") as f:
    f.write(resp.text)

soup = BeautifulSoup(resp.text, "lxml")

# Find all links
all_links = soup.find_all("a", href=True)
print(f"Total <a> tags: {len(all_links)}")

# Filter potential subject links
subject_candidates = []
for a in all_links:
    href = a["href"]
    if "class-" in href and "fbise-past-papers" in href:
        subject_candidates.append(href)
        print(f"Subject link candidate: {href} | Text: {a.get_text(strip=True)}")

print(f"\nFound {len(subject_candidates)} subject link candidates.")

# Also check for any div.entry-content
content_div = soup.find("div", class_="entry-content")
if content_div:
    print("\nFound div.entry-content")
    inner_links = content_div.find_all("a", href=True)
    print(f"Links inside entry-content: {len(inner_links)}")
