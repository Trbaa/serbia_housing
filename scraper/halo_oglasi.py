from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from urllib.parse import urljoin
from datetime import datetime
import psycopg2
from database.db_config import get_scraping_db_connection_params, ensure_connection
from database.insert_row import insert_row_halo, update_full_row_halo
from scraper.url_checker import check_url_status, extract_oglas_id, URL_NEW, URL_INCOMPLETE, URL_COMPLETE
import random
from preprocesing.pipeline import preprocess
from scraper.user_agents import get_context_kwargs
from scraper.url_checker import oglas_id_exists


BASE_URL = "https://www.halooglasi.com"
MAX_CONSECUTIVE_DUPLICATES = 3 
FAILED_LOG_FILE = "HALO_failed_pages_V02.txt"
def save_failed_page(url,error_message):
    with open(FAILED_LOG_FILE,"a",encoding="utf-8") as f:
        f.write(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"
            f"URL: {url} | ERROR: {error_message}\n"
        )

#Smanjuje opterecenje na context prozor
def block_resources(route):
    resource_type = route.request.resource_type
    url = route.request.url.lower()

    blocked_types = {"image", "media", "font"}
    blocked_keywords = [
        "doubleclick",
        "googletagmanager",
        "google-analytics",
        "facebook",
        "analytics",
        "ads",
    ]

    if resource_type in blocked_types or any(word in url for word in blocked_keywords):
        route.abort()
    else:
        route.continue_()

def close_halo_popups(page):
    try:
        popup_button = page.locator("button:has-text('U redu'), input[value='U redu'], a:has-text('U redu')")
        if popup_button.count() > 0:
            popup_button.first.click(timeout=2000)
            page.wait_for_timeout(1000)
    except Exception:
        pass

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

def protect_data(locator,field_name,url,timeout = 3000):
    try:
        if locator.count() == 0:
            return None
        text = locator.first.inner_text(timeout= timeout)
        if text:
            return text.strip() if text else None
    except Exception as e:
        save_failed_page(url,error_message=str(e))
        return None


def get_listing_urls(page, current_url):
    try:
        page.wait_for_selector("h3.product-title a", state="attached", timeout=20000)
        page.wait_for_timeout(1500)
    except Exception as e:
        save_failed_page(current_url, f"Listing load failed: {e}")
        return []

    links = page.locator("h3.product-title a")

    urls = []
    for i in range(links.count()):
        href = links.nth(i).get_attribute("href")
        if href:
            urls.append(urljoin(BASE_URL, href))

    return list(dict.fromkeys(urls))

def scrape_listing(context, url):
    page = context.new_page()
    human_delay(page)
    data = {col: None for col in CSV_COLUMNS}
    data["url"] = url
    data["oglas_id"] = extract_oglas_id(url,"halo_oglasi")
    
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        close_halo_popups(page)
        page.wait_for_selector("h1", state="attached", timeout=15000)
        page.wait_for_timeout(1500)



        # naslov
        data['title'] = protect_data(page.locator("h1"),'title',url)
        if data["title"] and "halooglasi" in data["title"].lower():
            save_failed_page(url, "Anti-bot page detected")
            return None
        
        # ukupna cena
        data['price_total'] =protect_data(page.locator("span[data-value]"),'price_total',url)
        # cena po kvadratu
        data['price_per_m2'] =protect_data(page.locator("div.price-by-surface span"),'price_per_m2',url)

        # gornji blok: Tip nekretnine / Kvadratura / Broj soba
        try:
            prominent_items = page.locator("div.prominent li")
            count = prominent_items.count()

            for i in range(prominent_items.count()):
                try:
                    item = prominent_items.nth(i)

                    field_name_locator = item.locator("span.field-name")
                    field_value_locator = item.locator("span.field-value")

                    if field_name_locator.count() == 0 or field_value_locator.count() == 0:
                        continue

                    field_name = field_name_locator.first.inner_text().strip()
                    field_value = field_value_locator.first.inner_text().strip()

                    if field_name in data:
                        data[field_name] = field_value
                except Exception as e:
                    save_failed_page(url,str(e))
        except Exception as e:
            save_failed_page(url,str(e))

        # desni datasheet blok: Oglašivač, Tip objekta, Sprat...
        try:
            detail_rows = page.locator("div.datasheet.product-basic-details div.basic-view")
            for i in range(detail_rows.count()):
                try:
                    row = detail_rows.nth(i)

                    cols = row.locator("div.row > div")
                    if cols.count() < 2:
                        continue

                    key = cols.nth(0).inner_text().strip()
                    value = cols.nth(1).inner_text().strip()

                    if key in data:
                        data[key] = value
                except Exception as e:
                    save_failed_page(url,str(e))
        except Exception as e:
            save_failed_page(url,str(e))

        # Dodatno + Ostalo
        # U tim sekcijama svaka pronađena stavka dobija vrednost "Da"
        feature_sections = ["Dodatno", "Ostalo"]

        for section_name in feature_sections:
            try:
                section_block = page.locator(
                    f"div.tab-attribute:has(div.tab-section-header label:text-is('{section_name}'))"
                )

                if section_block.count() == 0:
                    continue

                feature_labels = section_block.locator("div.flags-container span.flag-attribute label")

                for i in range(feature_labels.count()):
                    try:
                        feature_name =protect_data(feature_labels.nth(i),f"{section_name}_feature_{i}",url)

                        if feature_name in data:
                            data[feature_name] = "da"

                    except Exception as e:
                        save_failed_page(url,str(e))
            except Exception as e:
                save_failed_page(url,str(e))

            # Linije gradskog prevoza
        try:
            transport_block = page.locator("div.city-lines")

            if transport_block.count() > 0:
                line_items = transport_block.locator("ul li")
                lines = []

                for i in range(line_items.count()):
                    try:
                        line_text = protect_data(line_items.nth(i),f"line_item_{i}",url)
                        if line_text:
                            lines.append(line_text)
                    except Exception as e:
                        save_failed_page(url,str(e))
                if lines:
                    data["Linije gradskog prevoza"] = ", ".join(lines)
        except Exception as e:
            save_failed_page(url,str(e))


        #Date of posting
        try:
            date_row = page.locator("div.line", has_text="Objavljen")
            data["Datum_objave"] = protect_data(
                date_row.locator("span.value strong"),
                "Datum_objave", url, timeout=5000,
            )
            if data["Datum_objave"] is None:
                data["Datum_objave"] = protect_data(
                    page.locator("span.value strong").first,
                    "Datum_objave_fallback", url, timeout=3000,
                )
        except Exception as e:
            save_failed_page(url, f"datum block: {e}")


        # Dodatni opis
        try:
            description_block = page.locator(
                "div.tab-attribute:has(div.tab-section-header label:text-is('Dodatni opis'))"
            )

            if description_block.count() > 0:
                description_text = protect_data(description_block.locator("div.tab-top-group-attr-value span"),
                                                'Dodatni_opis',url)

                if description_text:
                    data["Dodatni opis"] = " ".join(description_text.split())
        except Exception as e:
            save_failed_page(url,str(e))

        return data

    except Exception as e:
            save_failed_page(url,str(e))
            return None
    
    finally:
        try:
            page.close()
        except Exception:
            pass



def scrape_all_pages_to_csv(listing_page, context, start_url, cursor, conn,
                             max_pages=None, mode="daily"):
    current_url          = start_url
    current_page_num     = 1
    seen_urls            = set()
    inserted_count       = 0
    consecutive_existing = 0  # brojač uzastopnih duplikata za daily mode
 
    max_pages_without_new_url = 5
    pages_without_new_url     = 0
 
    while True:
        print(f"\n[HALO] Obradjujem listing stranu {current_page_num}: {current_url}")
        listing_page.goto(current_url, wait_until="domcontentloaded")
        close_halo_popups(listing_page)
        listing_page.wait_for_timeout(2000)
 
        urls = get_listing_urls(listing_page, current_url)
        print(f"[HALO] Nadjeno oglasa na strani: {len(urls)}")
 
        if not urls:
            print("[HALO] Nema URL-ova. Kraj.")
            conn.commit()
            break
 
        new_urls_on_page = 0
        stop_early       = False
 
        for i, url in enumerate(urls, start=1):
            if url in seen_urls:
                continue
            seen_urls.add(url)
 
            try:
                oglas_id = extract_oglas_id(url, "halo_oglasi")
 
                if mode == "daily" and oglas_id_exists(cursor, oglas_id, "halo_oglasi"):
                    consecutive_existing += 1
                    print(f"  [{i}/{len(urls)}] [HALO] Postoji ({consecutive_existing}/{MAX_CONSECUTIVE_DUPLICATES}): {url}")
                    if consecutive_existing >= MAX_CONSECUTIVE_DUPLICATES:
                        print(f"  [HALO] {MAX_CONSECUTIVE_DUPLICATES} uzastopna duplikata — zaustavljam.")
                        stop_early = True
                        break
                    continue
 
                # Novi oglas — resetuj brojač
                consecutive_existing = 0
                new_urls_on_page += 1
 
                item = scrape_listing(context, url)
                if item is None:
                    continue
 
                item = preprocess(item)
                if item is None:
                    continue
 
                item["oglas_id"] = oglas_id
 
                if inserted_count > 0 and inserted_count % 50 == 0:
                    conn, cursor = ensure_connection(conn, cursor, get_scraping_db_connection_params)
 
                try:
                    insert_row_halo(cursor, item)
                except Exception:
                    conn.rollback()
                    conn, cursor = ensure_connection(conn, cursor, get_scraping_db_connection_params)
                    insert_row_halo(cursor, item)
 
                inserted_count += 1
                print(f"  [{i}/{len(urls)}] [HALO] INSERT: {url}")
 
                if inserted_count % 5 == 0:
                    conn.commit()
                    print(f"  [COMMIT] INSERT={inserted_count}")
 
            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                save_failed_page(url, str(e))
                print(f"[HALO] Greska za {url}: {e}")
 
        if stop_early:
            print(f"[HALO] Early stop — svi novi oglasi skrejpovani.")
            conn.commit()
            break
 
        if new_urls_on_page == 0:
            pages_without_new_url += 1
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
 
        current_page_num += 1
        current_url = f"{start_url}?page={current_page_num}"
 
    conn.commit()
    print(f"\n[HALO] ZAVRŠENO — INSERT={inserted_count}")

def run_halo_oglasi(max_pages = None,mode = "daily"):
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
        with Stealth().use_sync(sync_playwright()) as p:
            browser = p.chromium.launch(headless=True,slow_mo=300)

            context = browser.new_context(**get_context_kwargs())
            context.route("**/*", block_resources)

            context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            """)

            listing_page = context.new_page()
            #detail_page = context.new_page()

            start_url = "https://www.halooglasi.com/nekretnine/prodaja-stanova/beograd"


            scrape_all_pages_to_csv(
                    listing_page=listing_page,
                    context=context,
                    start_url=start_url,
                    cursor=cursor,
                    conn=conn,
                    max_pages=max_pages
                )
            listing_page.close()
            #detail_page.close()
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
