from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from urllib.parse import urljoin
from datetime import datetime
import psycopg2
from database.db_config import get_scraping_db_connection_params, ensure_connection
from database.insert_row import insert_row_nekretnine,insert_raw_row_nekretnine
from scraper.url_checker import oglas_id_exists, extract_oglas_id, duplicate_exists
import random
from preprocesing.pipeline import preprocess
from scraper.user_agents import get_context_kwargs

BASE_URL = "https://www.nekretnine.rs/"
FAILED_LOG_FILE = "NEKRETNINE_failed_pages_V02.txt"
MAX_CONSECUTIVE_DUPLICATES = 3

def save_failed_page(url, error_message):
    with open(FAILED_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"
            f"URL: {url} | ERROR: {error_message}\n"
        )

def block_resources(route):
    resource_type = route.request.resource_type
    url = route.request.url.lower()
    blocked_types = {"image", "media", "font"}
    blocked_keywords = [
        "doubleclick", "googletagmanager", "google-analytics",
        "facebook", "analytics", "ads",
    ]
    if resource_type in blocked_types or any(word in url for word in blocked_keywords):
        route.abort()
    else:
        route.continue_()

def human_delay(page, a=800, b=8000):
    page.wait_for_timeout(random.randint(a, b))

CSV_COLUMNS = [
    "url", "title", "price_total", "price_per_m2",
    "Tip nekretnine", "Kvadratura", "Broj soba", "Oglašivač",
    "Tip objekta", "Stanje objekta", "Grejanje", "Sprat",
    "Ukupna spratnost", "Uknjižen", "Terasa", "Interfon",
    "Klima", "Video nadzor", "Internet", "Parking", "Garaža",
    "Lift", "Podrum", "Linije gradskog prevoza",
    "Datum_objave", "Dodatni opis"
]

FIELD_MAP = {
    "Kategorija": "Tip nekretnine",
    "Ukupan broj soba": "Broj soba",
    "Spratnost": "Sprat",
    "Ukupan broj spratova": "Ukupna spratnost",
    "Stanje nekretnine": "Stanje objekta",
}

def protect_data(locator, field_name, url, timeout=3000):
    try:
        if locator.count() == 0:
            return None
        text = locator.first.inner_text(timeout=timeout)
        return text.strip() if text else None
    except Exception as e:
        save_failed_page(url, error_message=str(e))
        return None

def get_listings_url(page):
    page.wait_for_selector("h2.offer-title a", timeout=30000)
    links = page.locator("h2.offer-title a")
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

def extract_datum(page, url):
    try:
        updated_div = page.locator("div.updated")
        if updated_div.count() == 0:
            return None

        spans = updated_div.locator("span")
        objavljen = None
        azuriran  = None

        for i in range(spans.count()):
            try:
                text = spans.nth(i).inner_text(timeout=2000).strip()
                if not text:
                    continue
                if "Objavljen" in text:
                    objavljen = text.replace("Objavljen:", "").strip()
                elif "Ažuriran" in text or "Azuriran" in text:
                    azuriran = text.replace("Ažuriran:", "").replace("Azuriran:", "").strip()
            except Exception:
                continue

        return objavljen if objavljen else azuriran

    except Exception as e:
        save_failed_page(url, f"extract_datum: {e}")
        return None

def scrape_listings(context, url):
    page = context.new_page()
    data = {col: None for col in CSV_COLUMNS}
    data["url"] = url
    data["oglas_id"] = extract_oglas_id(url, "nekretnine_rs")

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        human_delay(page)

        data["title"] = protect_data(
            page.locator("h1.detail-title"), "title", url, timeout=3000
        )
        data["price_total"] = protect_data(
            page.locator("h4.stickyBox__price"), "price_total", url, timeout=3000
        )
        data["price_per_m2"] = protect_data(
            page.locator("h4.stickyBox__price span"), "price_per_m2", url
        )

        try:
            details_section = page.locator("section#detalji")
            amenity_blocks  = details_section.locator("div.property__amenities")

            for i in range(amenity_blocks.count()):
                try:
                    block = amenity_blocks.nth(i)
                    items = block.locator("li")
                    raw_features = []

                    for j in range(items.count()):
                        try:
                            li     = items.nth(j)
                            strong = li.locator("strong")

                            if strong.count() > 0:
                                full_text   = protect_data(li, f"detail_li_{i}_{j}", url, timeout=1500)
                                field_value = protect_data(strong, f"detail_strong_{i}_{j}", url, timeout=1500)

                                if not full_text or not field_value:
                                    continue

                                raw_field_name = full_text.split(":")[0].strip()
                                field_name     = FIELD_MAP.get(raw_field_name, raw_field_name)

                                if field_name in data:
                                    data[field_name] = field_value
                            else:
                                feature = protect_data(li, f"feature_li_{i}_{j}", url)
                                if feature:
                                    raw_features.append(feature)
                        except Exception as e:
                            save_failed_page(url, str(e))

                    map_features(raw_features, data)

                except Exception as e:
                    save_failed_page(url, str(e))
        except Exception as e:
            save_failed_page(url, str(e))

        data["Datum_objave"] = extract_datum(page, url)

        try:
            opis = protect_data(
                page.locator("section#opis .cms-content-inner"),
                "Dodatni_opis", url
            )
            if opis:
                data["Dodatni opis"] = " ".join(opis.split())
        except Exception as e:
            save_failed_page(url, str(e))

        return data

    except Exception as e:
        save_failed_page(url, str(e))
        return None
    finally:
        try:
            page.close()
        except Exception:
            pass


def scrape_all_pages(listing_page, context, start_url, cursor, conn,
                     max_pages=None, mode="daily"):
    current_url          = start_url
    current_page_num     = 1
    seen_urls            = set()
    inserted_count       = 0
    consecutive_existing = 0

    max_pages_without_new_url = 5
    pages_without_new_url     = 0
    hard_max_pages            = 1000

    while True:
        print(f"\n[NEKRETNINE] Obradjujem listing stranu {current_page_num}: {current_url}")
        listing_page.goto(current_url, wait_until="domcontentloaded")
        human_delay(listing_page)

        urls = get_listings_url(listing_page)
        print(f"[NEKRETNINE] Nadjeno oglasa na strani: {len(urls)}")

        if not urls:
            print("[NEKRETNINE] Nema URL-ova, prekid.")
            conn.commit()
            break

        new_urls_on_page = 0
        stop_early       = False

        for i, url in enumerate(urls, start=1):
            if url in seen_urls:
                continue
            seen_urls.add(url)

            try:
                oglas_id = extract_oglas_id(url, "nekretnine_rs")

                if mode == "daily" and oglas_id_exists(cursor, oglas_id, "nekretnine_rs"):
                    consecutive_existing += 1
                    print(f"  [{i}/{len(urls)}] [NEKRETNINE] Postoji ({consecutive_existing}/{MAX_CONSECUTIVE_DUPLICATES}): {url}")
                    if consecutive_existing >= MAX_CONSECUTIVE_DUPLICATES:
                        print(f"  [NEKRETNINE] {MAX_CONSECUTIVE_DUPLICATES} uzastopna duplikata — zaustavljam.")
                        stop_early = True
                        break
                    continue

                consecutive_existing = 0
                new_urls_on_page += 1

                item = scrape_listings(context, url)
                if item is None:
                    continue
                
                insert_raw_row_nekretnine(cursor,item)
                try:
                    insert_raw_row_nekretnine(cursor,item)
                except Exception:
                    conn.rollback()
                    conn, cursor = ensure_connection(conn, cursor, get_scraping_db_connection_params)
                    insert_raw_row_nekretnine(cursor,item)
                    
                item = preprocess(item)
                if item is None:
                    continue

                if duplicate_exists(cursor, item.get("title"), item.get("price_total"), 
                    item.get("kvadratura"), "nekretnine_rs"):
                    print(f"  [{i}/{len(urls)}] [NEKRETNINE] Duplikat (title+cena+kv): {url}")
                    continue

                item["oglas_id"] = oglas_id

                if inserted_count > 0 and inserted_count % 50 == 0:
                    conn, cursor = ensure_connection(conn, cursor, get_scraping_db_connection_params)

                try:
                    insert_row_nekretnine(cursor, item)
                except Exception:
                    conn.rollback()
                    conn, cursor = ensure_connection(conn, cursor, get_scraping_db_connection_params)
                    insert_row_nekretnine(cursor, item)

                inserted_count += 1
                print(f"  [{i}/{len(urls)}] [NEKRETNINE] INSERT: {url}")

                if inserted_count % 5 == 0:
                    conn.commit()
                    print(f"  [COMMIT] INSERT={inserted_count}")

            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                print(f"[NEKRETNINE] Greska za {url}: {e}")

        if stop_early:
            print(f"[NEKRETNINE] Early stop — svi novi oglasi skrejpovani.")
            conn.commit()
            break

        if new_urls_on_page == 0:
            pages_without_new_url += 1
            print(f"[NEKRETNINE] Strana bez novih URL-ova ({pages_without_new_url}/{max_pages_without_new_url})")
        else:
            pages_without_new_url = 0

        if pages_without_new_url >= max_pages_without_new_url:
            print("[NEKRETNINE] Pet strana zaredom bez novih oglasa, prekid.")
            conn.commit()
            break

        if max_pages is not None and current_page_num >= max_pages:
            print("[NEKRETNINE] Dostignut max_pages limit")
            break

        if current_page_num >= hard_max_pages:
            print("Safety stop: dostignut hard_max_pages.")
            conn.commit()
            break

        current_page_num += 1
        # Sortiranje od najnovijih + povećano na 20 oglasa po stranici
        current_url = (
            f"https://www.nekretnine.rs/stambeni-objekti/stanovi/"
            f"izdavanje-prodaja/prodaja/grad/beograd/lista/po-stranici/20/"
            f"stranica/{current_page_num}/?order=2"
        )

    conn.commit()
    print(f"\n[NEKRETNINE] ZAVRSENO — INSERT={inserted_count}")


def run_nekretnine(max_pages=None, mode="daily"):
    conn   = None
    cursor = None

    try:
        conn = psycopg2.connect(
            **get_scraping_db_connection_params(),
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
        )
        cursor = conn.cursor()

        with Stealth().use_sync(sync_playwright()) as p:
            browser = p.chromium.launch(headless=True, slow_mo=100)
            context = browser.new_context(**get_context_kwargs())
            context.route("**/*", block_resources)
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            listing_page = context.new_page()
            # Sortiranje od najnovijih (?order=2)
            start_url = (
                "https://www.nekretnine.rs/stambeni-objekti/stanovi/"
                "izdavanje-prodaja/prodaja/grad/beograd/lista/po-stranici/20/?order=2"
            )

            scrape_all_pages(
                listing_page=listing_page,
                context=context,
                start_url=start_url,
                cursor=cursor,
                conn=conn,
                max_pages=max_pages,
                mode=mode,
            )

            listing_page.close()
            context.close()
            browser.close()

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Greska u nekretnine: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()