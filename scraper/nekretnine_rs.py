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

BASE_URL = "https://www.nekretnine.rs/"

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
    "Datum_objave",
    "Dodatni opis"
]
#mapiranje jer nisu isti nazivi na sajtu
FIELD_MAP = {
    "Kategorija": "Tip nekretnine",
    "Ukupan broj soba": "Broj soba",
    "Spratnost": "Sprat",
    "Ukupan broj spratova": "Ukupna spratnost",
    "Stanje nekretnine": "Stanje objekta",
}

def get_listings_url(page):
    page.wait_for_selector("h2.offer-title a")
    links = page.locator("h2.offer-title a")

    urls = []
    for i in range(links.count()):
        href = links.nth(i).get_attribute("href")
        if href:
            urls.append(urljoin(BASE_URL,href))
        
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

    page.goto(url,wait_until="domcontentloaded")
    human_delay(page)

    data = {col: None for col in CSV_COLUMNS}
    data["url"] = url

    #naslov
    title_locator = page.locator("h1.detail-title")
    if title_locator.count() > 0:
        data["title"] = title_locator.first.inner_text().strip()

     #Ukupna cena
    price_locator = page.locator("h4.stickyBox__price")
    if price_locator.count() > 0:
        data["price_total"] = price_locator.first.inner_text().strip()

      # cena po kvadratu
    m2_locator = page.locator("h4.stickyBox__price span")
    if m2_locator.count() > 0:
        data["price_per_m2"] = m2_locator.first.inner_text().strip()
    
    # gornji blok: Tip nekretnine / Kvadratura / Broj soba
    details_section = page.locator("section#detalji")
    amenity_blocks = details_section.locator("div.property__amenities")
    for i in range(amenity_blocks.count()):
        block = amenity_blocks.nth(i)
        title = block.locator("h3").inner_text().strip()

        items = block.locator("li")
        raw_features = []

        for j in range(items.count()):
            li = items.nth(j)
            strong = li.locator("strong")

            if strong.count() > 0:
                raw_field_name = li.inner_text().split(":")[0].strip()
                field_value = strong.inner_text().strip()

                field_name = FIELD_MAP.get(raw_field_name, raw_field_name)

                if field_name in data:
                    data[field_name] = field_value
            else:
                feature = li.inner_text().strip()
                raw_features.append(feature)

        map_features(raw_features, data)

    #datum_objave
    raw_datum = page.locator("div.updated span").nth(1).inner_text().strip()

    if raw_datum.startswith("Objavljen:"):
        data["Datum_objave"] = raw_datum.replace("Objavljen:", "").strip()

    #dodatni opis
    opis_oglasa = page.locator("section#opis .cms-content-inner")
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
            current_url = "https://www.nekretnine.rs/stambeni-objekti/stanovi/izdavanje-prodaja/prodaja/grad/beograd/lista/po-stranici/10/"
        else:
            current_url = f"https://www.nekretnine.rs/stambeni-objekti/stanovi/izdavanje-prodaja/prodaja/grad/beograd/lista/po-stranici/10/stranica/{current_page_num}"


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False,slow_mo=100)

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
    details_page = context.new_page()

    start_url = "https://www.nekretnine.rs/stambeni-objekti/stanovi/izdavanje-prodaja/prodaja/grad/beograd/lista/po-stranici/10/"

    with open("nekretnine_rs_raw.csv","w",newline="",encoding="utf-8") as f:
        writer = csv.DictWriter(f,fieldnames=CSV_COLUMNS)
        writer.writeheader()

        scrape_all_pages(
            listing_page=listing_page,
            detail_page=details_page,
            start_url=start_url,
            writer=writer,
            max_pages=3, #OVO PROMENITI KASNIJE
        )
    
    listing_page.close()
    details_page.close()
    browser.close()