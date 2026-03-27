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
    links = page.locator("a").filter(has_text="Beograd").filter(has_text="€/m²") ## samo za kartice gde se pominje Beograd i ima znak €/m²
    urls = []
    for i in range(links.count()):
        href = links.nth(i).get_attribute("href")
        if href:
            urls.append(urljoin(BASE_URL, href))

    return list(dict.fromkeys(urls))


def map_features(raw_features, data):
    for item in raw_features:
        text = item.lower()

        if "grejanje" in text:
            data["Grejanje"] = item

        if "uknjižen" in text or "uknjizen" in text:
            data["Uknjižen"] = "da"

        if "terasa" in text:
            data["Terasa"] = "da"

        if "interfon" in text:
            data["Interfon"] = "da"

        if "klima" in text:
            data["Klima"] = "da"

        if "internet" in text:
            data["Internet"] = "da"

        if "agencija" in text:
            data["Oglašivač"] = "agencija"

        if "stanje" in text:
            data["Stanje objekta"] = item

        if "podrum" in text:
            data["Podrum"] = "da"

        if "lift" in text:
            data["Lift"] = "da"

        if "parking" in text:
            data["Parking"] = "da"

        if "garaža" in text or "garaza" in text:
            data["Garaža"] = "da"

    return data

def scrape_listings(page,url):
    page.goto(url, wait_until="domcontentloaded")
    human_delay(page)

    data = {col: None for col in CSV_COLUMNS}
    data["url"] = url


    title_locator = page.locator("h1")
    if title_locator.count() > 0:
        data["title"] = title_locator.first.inner_text().strip()

    price_total_loc = page.locator('p[test-data="ad-price"]')
    if price_total_loc.count() > 0:
        data["price_total"] = price_total_loc.first.inner_text().strip()

    price_per_m2 = page.locator('div.text-right p').nth(1)
    if price_per_m2.count() > 0:
        data["price_per_m2"] = price_per_m2.first.inner_text().strip()

    details = page.locator("div.flex.gap-px strong")
    if details.count() > 0:
        data['Kvadratura'] = details.nth(0).first.inner_text().strip()
        data['Broj soba'] = details.nth(1).first.inner_text().strip()

        sprat_text = details.nth(2).inner_text().strip()   # npr. 5/5 spratova
        parts = sprat_text.split("/")

        if len(parts) == 2:
            data["Sprat"] = parts[0].strip()
            data["Ukupna spratnost"] = parts[1].replace("spratova", "").replace("sprata", "").strip()
    
        raw_features = []

    stan_section = page.locator("section").filter(has=page.locator('strong:has-text("O stanu")'))

    if stan_section.count() > 0:
        feature_items = stan_section.first.locator("li span")

        for i in range(feature_items.count()):
            text = feature_items.nth(i).inner_text().strip()
            if text:
                raw_features.append(text)

    data = map_features(raw_features, data)

    opis_oglasa = page.locator('div[test-data="rich-text-description"] div.flex.w-full.flex-col.gap-4.whitespace-normal')
    if opis_oglasa.count() > 0:
        data["Dodatni opis"] = " ".join(opis_oglasa.first.inner_text().split())

    return data

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
        title = scrape_listings(page,i)
        print(title)
    browser.close()