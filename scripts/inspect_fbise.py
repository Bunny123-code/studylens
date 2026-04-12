# inspect_fbise.py (updated)
import requests
from bs4 import BeautifulSoup

url = "https://fbisepastpapers.com/class-9-fbise-past-papers/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, "lxml")

content_div = soup.find("div", class_="entry-content")
if content_div:
    links = content_div.find_all("a", href=True)
    print(f"Total links in entry-content: {len(links)}")
    for a in links[:30]:  # Show first 30 for brevity
        href = a["href"]
        text = a.get_text(strip=True)
        print(f"{href}  -->  {text}")
else:
    print("No entry-content div found.")
