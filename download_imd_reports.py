import os
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

BASE_URL = "https://metnet.imd.gov.in/phps/imdweb_imdarep.php"
DOWNLOAD_DIR = "data/raw_pdfs/imd_reports"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def download_file(url, filepath):
    try:
        with requests.get(url, stream=True, timeout=60) as r:
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
        print(f"❌ Failed: {url} — {e}")
        return False

def download_imd_reports(start_year=2008, end_year=2024):
    print(f"Fetching IMD annual reports ({start_year}–{end_year})...")
    response = requests.get(BASE_URL, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    pdf_links = [a["href"] for a in soup.find_all("a", href=True) if a["href"].endswith(".pdf")]
    print(f"Found {len(pdf_links)} possible report links.")

    downloaded = 0
    for pdf_url in pdf_links:
        for year in range(start_year, end_year + 1):
            if str(year) in pdf_url:
                filename = f"IMD_Annual_Report_{year}.pdf"
                filepath = os.path.join(DOWNLOAD_DIR, filename)
                if os.path.exists(filepath):
                    print(f"✔️ Already downloaded: {filename}")
                    break

                if not pdf_url.startswith("http"):
                    pdf_url = "https://metnet.imd.gov.in/phps/" + pdf_url

                print(f"📥 Downloading {filename} ...")
                if download_file(pdf_url, filepath):
                    downloaded += 1
                break

    print(f"\n✅ Done! {downloaded} IMD reports saved in {DOWNLOAD_DIR}")

if __name__ == "__main__":
    download_imd_reports(2008, 2024)
