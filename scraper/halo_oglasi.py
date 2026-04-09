from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
import psycopg2
from database.db_config import get_scraping_db_connection_params,ensure_connection
from database.insert_row import insert_row_halo
import random
from datetime import datetime
from preprocesing.pipeline import preprocess
from scraper.user_agents import get_context_kwargs

BASE_URL = "https://www.halooglasi.com"

FAILED_LOG_FILE = "HALO_failed_pages.txt"
def save_failed_page(url,error_message):
    with open(FAILED_LOG_FILE,"a",encoding="utf-8") as f:
        f.write(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"
            f"URL: {url} | ERROR: {error_message}\n"
        )

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
    data = {col: None for col in CSV_COLUMNS}
    data["url"] = url
    
    try:
        page.goto(url, wait_until="domcontentloaded")
        human_delay(page)


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
                    data[feature_name] = "da"

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

        #Date of posting
        date = page.locator('div.line').filter(
            has = page.locator("label.description:has-text('Objavljen')")
        )
        #Bolje je da sakupi celu vrednost a pipeline da ocisti
        raw_date = date.locator('span.value strong').inner_text().strip()
        data["Datum_objave"] = raw_date


    # Dodatni opis
        description_block = page.locator(
            "div.tab-attribute:has(div.tab-section-header label:text-is('Dodatni opis'))"
        )

        if description_block.count() > 0:
            description_text = description_block.locator("div.tab-top-group-attr-value span")

            if description_text.count() > 0:
                data["Dodatni opis"] = description_text.first.inner_text().strip()
    except Exception as e:
        save_failed_page(url,str(e))
        return data

    return data


def scrape_all_pages_to_csv(listing_page, detail_page, start_url,cursor, conn, max_pages=None):
    current_url = start_url
    current_page_num = 1
    seen_urls = set()
    inserted_count = 0

    max_pages_without_new_url = 5
    pages_without_new_url = 0

    while True:
        print(f"\n[HALO] Obradjujem listing stranu {current_page_num}: {current_url}")

        listing_page.goto(current_url, wait_until="domcontentloaded")
        human_delay(detail_page)

        urls = get_listing_urls(listing_page)
        print(f"[HALO] Nadjeno oglasa na strani: {len(urls)}")

        if not urls:
            print("[HALO] Nema URL-ova. Kraj.")
            conn.commit()
            break
        new_urls_on_page = 0
        for i, url in enumerate(urls, start=1):
            if url in seen_urls:
                continue

            seen_urls.add(url)
            new_urls_on_page += 1

            try:
                item = scrape_listing(detail_page, url)
                if item is None:
                    continue

                item= preprocess(item)
                if item is None:
                    continue
                    
                if inserted_count > 0 and inserted_count % 50 == 0:
                    conn, cursor = ensure_connection(conn, cursor, get_scraping_db_connection_params)
                try:
                    insert_row_halo(cursor,item)
                except Exception:
                    conn.rollback()
                    conn,cursor = ensure_connection(conn,cursor,get_scraping_db_connection_params)
                    insert_row_halo(cursor,item) # #probam retry unosa
                inserted_count += 1

                if inserted_count > 0 and inserted_count % 20 == 0:
                    conn.commit()
                if inserted_count % 35 == 0:
                    human_delay(listing_page,30000,90000)

                print(f"  [{i}/{len(urls)}] [HALO] Sacuvan: {url}")
                human_delay(detail_page)
            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                print(f"[HALO] Greska za {url}: {e}")

        if new_urls_on_page == 0:
            pages_without_new_url +=1
            print(f"[HALO] Strana bez novih URL-ova ({pages_without_new_url}/{max_pages_without_new_url})")
        else:
            pages_without_new_url = 0
            
        if pages_without_new_url >= max_pages_without_new_url:
            print("[HALO] Pet strana zaredom bez novih oglasa, prekid.")
            conn.commit()
            break

        if max_pages is not None and current_page_num >= max_pages:
            print("[HALO] Dostignut max_pages limit.")
            break

        next_button = listing_page.locator("a.page-link.next")

        if next_button.count() == 0:
            print("[HALO] Nema sledece strane. Kraj.")
            conn.commit()
            break

        next_href = next_button.first.get_attribute("href")
        if not next_href:
            print("[HALO] Sledeca strana nema href. Kraj.")
            conn.commit()
            break

        current_url = urljoin(BASE_URL, next_href)
        current_page_num += 1
    conn.commit()

def run_halo_oglasi(max_pages = 3):
    conn = None
    cursor = None

    try:
        conn = psycopg2.connect(
            **get_scraping_db_connection_params(),
            keepalives = 1,
            keepalives_idle = 30,
            keepalives_interval = 10,
            keepalives_count = 5)
        
        cursor = conn.cursor()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False,slow_mo=100)

            context = browser.new_context(**get_context_kwargs())

            context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            """)

            listing_page = context.new_page()
            detail_page = context.new_page()

            start_url = "https://www.halooglasi.com/nekretnine/prodaja-stanova/beograd"


            scrape_all_pages_to_csv(
                    listing_page=listing_page,
                    detail_page=detail_page,
                    start_url=start_url,
                    cursor=cursor,
                    conn=conn,
                    max_pages=max_pages
                )
            listing_page.close()
            detail_page.close()
            context.close()
            browser.close()
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Greska u run_halo_oglasi: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()