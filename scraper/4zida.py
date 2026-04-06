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

def human_delay(page, a=800, b=8000):
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
    "Interfon",
    "Klima",
    "Video nadzor",
    "Internet",
    "Parking",
    "Garaža",
    'Lift',
    "Podrum",
    "Linije gradskog prevoza",
    "Datum_objave",
    "Dodatni opis"
]

def get_listings_url(page):
    page.wait_for_selector('a[href*="/prodaja-stanova/"]')
    human_delay(page)
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

    #date_of posting
    raw_datum = page.locator("span.text-gray-600").filter(has_text="Oglas ažuriran:")
    datum = raw_datum.locator("span.font-medium").first.inner_text().strip()
    data["Datum_objave"] = datum

    #Opis oglasa - veliki tekst
    opis_oglasa = page.locator('div[test-data="rich-text-description"] div.flex.w-full.flex-col.gap-4.whitespace-normal')
    if opis_oglasa.count() > 0:
        data["Dodatni opis"] = " ".join(opis_oglasa.first.inner_text().split())

    return data


def scrape_all_pages(listing_page,detail_page,start_url,writer,max_pages = None):
    current_url = start_url
    current_page_num = 1
    seen_urls = set()

    while True:
        print(f"\nObradjujem listing stranu {current_page_num}: {current_url}")
        listing_page.goto(current_url,wait_until = 'domcontentloaded')
        human_delay(listing_page)

        urls = get_listings_url(listing_page)
        print(f"Nadjeno oglasa na strani: {len(urls)}")

        for i,url in enumerate(urls,start = 1):
            if url in seen_urls:
                continue
            seen_urls.add(url)

            try:
                item =scrape_listings(detail_page,url)
                writer.writerow(item)
                print(f"  [{i}/{len(urls)}] Sacuvan: {url}")
                human_delay(detail_page)
            except Exception as e:
                print(f"Greska za {url}:{e}")

        if max_pages is not None and current_page_num >=max_pages:
            print("Dostignut max_pages limit")
            break
            
       
        current_page_num +=1
        if current_page_num == 1:
            current_url = "https://www.4zida.rs/prodaja-stanova/beograd"
        else:
            current_url = f"https://www.4zida.rs/prodaja-stanova/beograd?strana={current_page_num}"
        

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
    user_agent=random.choice(USER_AGENTS),
    viewport={"width": 1366, "height": 768},
    locale="sr-RS",
    extra_http_headers={
        "Accept-Language": "sr-RS,sr;q=0.9,en-US;q=0.8,en;q=0.7"
    }
)

    context.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
    """)

    listing_page = context.new_page()
    detail_page = context.new_page()


    start_url = "https://www.4zida.rs/prodaja-stanova/beograd"
    
    with open("4zida_raw.csv","w",newline="",encoding="utf-8") as f:
        writer = csv.DictWriter(f,fieldnames=CSV_COLUMNS)
        writer.writeheader()

        scrape_all_pages(
            listing_page=listing_page,
            detail_page=detail_page,
            start_url=start_url,
            writer=writer,
            max_pages=3, #OVO PROMENITI KASNIJE
        )
    
    listing_page.close()
    detail_page.close()
    browser.close()