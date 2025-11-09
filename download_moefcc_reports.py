import os
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

BASE_URL = "https://moef.gov.in/annual-reports"
DOWNLOAD_DIR = "data/raw_pdfs"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def safe_filename(name):
    return name.replace("/", "_").replace(" ", "_")

def download_file(url, filepath):
    try:
        with requests.get(url, stream=True, allow_redirects=True, timeout=60) as r:
            r.raise_for_status()
            total_size = int(r.headers.get("content-length", 0))
            with open(filepath, "wb") as f, tqdm(
                total=total_size, unit="B", unit_scale=True, desc=os.path.basename(filepath)
            ) as pbar:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        return True
    except Exception as e:
        print(f"❌ Failed: {url} → {e}")
        return False

def download_reports(start_year=2005, end_year=2025):
    response = requests.get(BASE_URL, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    pdf_links = [
        link["href"] for link in soup.find_all("a", href=True)
        if link["href"].lower().endswith(".pdf")
    ]

    downloaded = 0
    for pdf_url in pdf_links:
        for year in range(start_year, end_year + 1):
            if str(year) in pdf_url:
                filename = f"MoEFCC_Annual_Report_{year}.pdf"
                filepath = os.path.join(DOWNLOAD_DIR, safe_filename(filename))

                if os.path.exists(filepath):
                    print(f"✔️ Already downloaded: {filename}")
                    break

                if not pdf_url.startswith("http"):
                    pdf_url = "https://moef.gov.in" + pdf_url

                print(f"📥 Downloading {filename} ...")
                if download_file(pdf_url, filepath):
                    downloaded += 1
                break

    print(f"\n✅ Done! {downloaded} reports saved in {DOWNLOAD_DIR}")

if __name__ == "__main__":
    download_reports(2005, 2025)
