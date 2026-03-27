from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
import csv

BASE_URL = "https://www.halooglasi.com"

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


def get_listing_urls(page):
    page.wait_for_selector("h3.product-title a")
    links = page.locator("h3.product-title a")

    urls = []
    for i in range(links.count()):
        href = links.nth(i).get_attribute("href")
        if href:
            urls.append(urljoin(BASE_URL, href))

    return list(dict.fromkeys(urls))


def scrape_listing(page, url):
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(1000)

    data = {col: None for col in CSV_COLUMNS}
    data["url"] = url

    # naslov
    title_locator = page.locator("h1")
    if title_locator.count() > 0:
        data["title"] = title_locator.first.inner_text().strip()

    # ukupna cena
    price_locator = page.locator("span[data-value]")
    if price_locator.count() > 0:
        data["price_total"] = price_locator.first.inner_text().strip()

    # cena po kvadratu
    m2_locator = page.locator("div.price-by-surface span")
    if m2_locator.count() > 0:
        data["price_per_m2"] = m2_locator.first.inner_text().strip()

    # gornji blok: Tip nekretnine / Kvadratura / Broj soba
    prominent_items = page.locator("div.prominent li")
    for i in range(prominent_items.count()):
        item = prominent_items.nth(i)

        field_name_locator = item.locator("span.field-name")
        field_value_locator = item.locator("span.field-value")

        if field_name_locator.count() == 0 or field_value_locator.count() == 0:
            continue

        field_name = field_name_locator.first.inner_text().strip()
        field_value = field_value_locator.first.inner_text().strip()

        if field_name in data:
            data[field_name] = field_value

    # desni datasheet blok: Oglašivač, Tip objekta, Sprat...
    detail_rows = page.locator("div.datasheet.product-basic-details div.basic-view")
    for i in range(detail_rows.count()):
        row = detail_rows.nth(i)

        cols = row.locator("div.row > div")
        if cols.count() < 2:
            continue

        key = cols.nth(0).inner_text().strip()
        value = cols.nth(1).inner_text().strip()

        if key in data:
            data[key] = value

    # Dodatno + Ostalo
    # U tim sekcijama svaka pronađena stavka dobija vrednost "Da"
    feature_sections = ["Dodatno", "Ostalo"]

    for section_name in feature_sections:
        section_block = page.locator(
            f"div.tab-attribute:has(div.tab-section-header label:text-is('{section_name}'))"
        )

        if section_block.count() == 0:
            continue

        feature_labels = section_block.locator("div.flags-container span.flag-attribute label")

        for i in range(feature_labels.count()):
            feature_name = feature_labels.nth(i).inner_text().strip()

            if feature_name in data:
                data[feature_name] = "Da"

        # Linije gradskog prevoza
    transport_block = page.locator("div.city-lines")

    if transport_block.count() > 0:
        line_items = transport_block.locator("ul li")
        lines = []

        for i in range(line_items.count()):
            line_text = line_items.nth(i).inner_text().strip()
            if line_text:
                lines.append(line_text)

        if lines:
            data["Linije gradskog prevoza"] = ", ".join(lines)

   # Dodatni opis
    description_block = page.locator(
        "div.tab-attribute:has(div.tab-section-header label:text-is('Dodatni opis'))"
    )

    if description_block.count() > 0:
        description_text = description_block.locator("div.tab-top-group-attr-value span")

        if description_text.count() > 0:
            data["Dodatni opis"] = description_text.first.inner_text().strip()


    return data


def scrape_all_pages_to_csv(listing_page, detail_page, start_url, writer, max_pages=None):
    current_url = start_url
    current_page_num = 1
    seen_urls = set()

    while True:
        print(f"\nObradjujem listing stranu {current_page_num}: {current_url}")

        listing_page.goto(current_url, wait_until="domcontentloaded")
        listing_page.wait_for_timeout(1500)

        urls = get_listing_urls(listing_page)
        print(f"Nadjeno oglasa na strani: {len(urls)}")

        for i, url in enumerate(urls, start=1):
            if url in seen_urls:
                continue

            seen_urls.add(url)

            try:
                item = scrape_listing(detail_page, url)
                writer.writerow(item)
                print(f"  [{i}/{len(urls)}] Sacuvan: {url}")
                detail_page.wait_for_timeout(1000)
            except Exception as e:
                print(f"  Greska za {url}: {e}")

        if max_pages is not None and current_page_num >= max_pages:
            print("Dostignut max_pages limit.")
            break

        next_button = listing_page.locator("a.page-link.next")

        if next_button.count() == 0:
            print("Nema sledece strane. Kraj.")
            break

        next_href = next_button.first.get_attribute("href")
        if not next_href:
            print("Sledeca strana nema href. Kraj.")
            break

        current_url = urljoin(BASE_URL, next_href)
        current_page_num += 1

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    
    listing_page = browser.new_page()
    detail_page = browser.new_page()

    start_url = "https://www.halooglasi.com/nekretnine/prodaja-stanova/beograd"

    detail_page = browser.new_page()

    with open("nekretnine.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()

        scrape_all_pages_to_csv(
            listing_page=listing_page,
            detail_page=detail_page,
            start_url=start_url,
            writer=writer,
            max_pages=3,   # stavi npr 3 dok testiras
        )

    listing_page.close()

    detail_page.close()
    browser.close()