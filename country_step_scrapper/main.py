import csv
import logging
import os
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://www.copperknob.co.uk/search?Order=Rating&Lang=Any&SearchType=Any&Level=Any&Beat=-1&Wall=-1&Search=&recnum={}"
DELAY = 2  # seconds for JS to load


def scrape_page(offset):
    url = BASE_URL.format(offset)
    logger.info(f"Opening Selenium for offset {offset}")
    options = Options()
    options.headless = True
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(DELAY)
    html = driver.page_source
    driver.quit()
    logger.info(f"Fetched and rendered page at offset {offset}")
    return html


def parse(html, offset):
    soup = BeautifulSoup(html, "html.parser")
    results = []
    items = soup.select("div.listitem")
    logger.info(f"Offset {offset} → found {len(items)} items")
    for item in items:
        # Title and link
        title_tag = item.select_one("div.listTitle a span.listTitleColor1")
        title = title_tag.get_text(strip=True) if title_tag else ""
        link_tag = item.select_one("div.listTitle a")
        link = link_tag["href"] if link_tag else ""
        # Author and date
        author_tag = item.select_one("div.listTitle span.listTitleColor2")
        author_and_date = author_tag.get_text(strip=True) if author_tag else ""
        # Details from the info line
        info_tag = item.select_one("div.listInfo p.listIcons")
        info = info_tag.get_text(separator=" ", strip=True) if info_tag else ""
        results.append(
            {
                "title": title,
                "link": link,
                "author_and_date": author_and_date,
                "info": info,
            }
        )
    return results


CHECKPOINT_FILE = "scrape_checkpoint.txt"


def save_checkpoint(offset):
    with open(CHECKPOINT_FILE, "w") as f:
        f.write(str(offset))


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            return int(f.read().strip())
    return 0


def main():
    offset = load_checkpoint()
    fieldnames = ["title", "link", "author_and_date", "info"]

    options = Options()
    options.headless = True
    driver = webdriver.Chrome(options=options)

    # Only write header if starting from zero
    if offset == 0:
        with open("copperknob.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

    try:
        while True:
            url = BASE_URL.format(offset)
            logger.info(f"Loading {url}")
            driver.get(url)
            time.sleep(DELAY)
            html = driver.page_source
            results = parse(html, offset)
            if not results:
                break

            # Append results to CSV
            with open("copperknob.csv", "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerows(results)

            logger.info(f"Wrote {len(results)} records from offset {offset}.")
            offset += len(results)
            save_checkpoint(offset)
    finally:
        driver.quit()

    logger.info("Scraping complete.")


if __name__ == "__main__":
    main()
