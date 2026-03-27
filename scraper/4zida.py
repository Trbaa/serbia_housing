from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
import csv
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",

    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",

    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

BASE_URL = "https://www.4zida.rs"

def human_delay(page, a=800, b=2000):
    page.wait_for_timeout(random.randint(a, b))

CSV_COLUMNS = [
    "url",
    "title",
    "price_total",
    "price_per_m2",
    "Tip nekretnine",
    "Kvadratura",
    "Broj soba",
    "Oglašivač",
    "Tip objekta",
    "Stanje objekta",
    "Grejanje",
    "Sprat",
    "Ukupna spratnost",
    "Uknjižen",
    "Terasa",
    "Telefon",
    "Interfon",
    "Klima",
    "Video nadzor",
    "Topla voda",
    "Internet",
    "Parking",
    "Garaža",
    'Lift',
    "Podrum",
    "Linije gradskog prevoza",
    "Dodatni opis"
]

def get_listings_url(page):
    page.wait_for_selector('a[href*="/prodaja-stanova/"]')
    links = page.locator('a[href*="/prodaja-stanova/"]')
    
    urls = []
    for i in range(links.count()):
        href = links.nth(i).get_attribute("href")
        if href:
            urls.append(urljoin(BASE_URL, href))

    return list(dict.fromkeys(urls))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    context = browser.new_context()
    page = context.new_page()

    start_url = "https://www.4zida.rs/prodaja-stanova/beograd"
    page.goto(start_url, wait_until="domcontentloaded")

    page.wait_for_timeout(5000)  # samo za debug
    

    cards = get_listings_url(page)
    print("Broj kartica:", len(cards))

    for i in cards:
        print(i)

    browser.close()