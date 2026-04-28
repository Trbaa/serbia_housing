from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from urllib.parse import urljoin
from datetime import datetime
import psycopg2
from database.db_config import get_scraping_db_connection_params, ensure_connection
from database.insert_row import insert_row_4zida,insert_raw_row_4zida
from scraper.url_checker import oglas_id_exists, extract_oglas_id, duplicate_exists
import random
from preprocesing.pipeline import preprocess
from scraper.user_agents import get_context_kwargs

BASE_URL = "https://www.4zida.rs"
FAILED_LOG_FILE = "Z4IDA_failed_pages_V02.txt"
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

def get_listings_url(page):
    for attempt in range(1, 4):
        try:
            page.wait_for_selector('[test-data="ad-search-card"]', timeout=20000)
            break
        except Exception as e:
            print(f"[4ZIDA] Timeout na listingu, pokušaj {attempt}/3")
            if attempt == 3:
                return []
            page.wait_for_timeout(random.randint(3000, 7000))
            page.reload(wait_until="domcontentloaded")

    hrefs = page.locator(
        '[test-data="ad-search-card"] a[href*="/prodaja-stanova/"]'
    ).evaluate_all("""
        els => els.map(el => el.getAttribute('href')).filter(Boolean)
    """)
    urls = []
    for href in hrefs:
        full_url = urljoin(BASE_URL, href)
        if "-stan/" in full_url:
            urls.append(full_url)
    return list(dict.fromkeys(urls))

def protect_data(locator, field_name, url, timeout=3000):
    try:
        if locator.count() == 0:
            return None
        text = locator.first.inner_text(timeout=timeout)
        return text.strip() if text else None
    except Exception as e:
        save_failed_page(url, error_message=str(e))
        return None

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
        datum_loc = page.locator("span.text-gray-600").filter(
            has_text="Oglas ažuriran:"
        ).locator("span.font-medium")

        if datum_loc.count() > 0:
            text = datum_loc.first.inner_text(timeout=3000).strip()
            if text:
                return text

        all_spans = page.locator("span.text-gray-600")
        for i in range(all_spans.count()):
            try:
                text = all_spans.nth(i).inner_text(timeout=1000).strip()
                if "ažuriran" in text.lower() or "azuriran" in text.lower():
                    parts = text.split(":")
                    if len(parts) >= 2:
                        return parts[-1].strip()
            except Exception:
                continue
        return None
    except Exception as e:
        save_failed_page(url, f"extract_datum: {e}")
        return None

def scrape_listings(context, url):
    page = context.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    human_delay(page)

    try:
        data = {col: None for col in CSV_COLUMNS}
        data["url"] = url
        data["oglas_id"] = extract_oglas_id(url, "z4ida")
        raw_features = []

        data["title"]        = protect_data(page.locator("h1"), "title", url)
        data["price_total"]  = protect_data(page.locator('p[test-data="ad-price"]'), "price_total", url)
        data["price_per_m2"] = protect_data(page.locator("div.text-right p").nth(1), "price_per_m2", url)

        details = page.locator("div.flex.gap-px strong")
        try:
            count = details.count()
            if count >= 1:
                data["Kvadratura"] = details.nth(0).first.inner_text().strip()
            if count >= 2:
                data["Broj soba"] = details.nth(1).first.inner_text().strip()
            if count >= 3:
                sprat_text = details.nth(2).inner_text().strip()
                parts = sprat_text.split("/")
                if len(parts) == 2:
                    data["Sprat"] = parts[0].strip()
                    data["Ukupna spratnost"] = (
                        parts[1].replace("spratova", "").replace("sprata", "").strip()
                    )
        except Exception as e:
            save_failed_page(url, str(e))

        try:
            stan_section = page.locator("section").filter(
                has=page.locator('strong:has-text("O stanu")')
            )
            if stan_section.count() > 0:
                feature_items = stan_section.first.locator("li span")
                for i in range(feature_items.count()):
                    try:
                        text = feature_items.nth(i).inner_text().strip()
                        if text:
                            raw_features.append(text)
                    except Exception as e:
                        save_failed_page(url, str(e))
        except Exception as e:
            save_failed_page(url, str(e))

        map_features(raw_features, data)
        data["Datum_objave"] = extract_datum(page, url)

        opis = protect_data(
            page.locator('div[test-data="rich-text-description"] div.flex.w-full.flex-col.gap-4.whitespace-normal'),
            "Dodatni_opis", url
        )
        if opis:
            data["Dodatni opis"] = " ".join(opis.split())

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
        print(f"\n[4ZIDA] Obradjujem listing stranu {current_page_num}: {current_url}")

        try:
            listing_page.goto(current_url, wait_until="domcontentloaded")
            human_delay(listing_page)
        except Exception as e:
            print(f"[4ZIDA] Greška pri učitavanju listing stranice {current_page_num}: {e}")
            pages_without_new_url += 1
            if pages_without_new_url >= max_pages_without_new_url:
                break
            current_page_num += 1
            current_url = f"https://www.4zida.rs/prodaja-stanova/beograd?sortiranje=najnoviji&strana={current_page_num}"
            continue

        urls = get_listings_url(listing_page)
        print(f"[4ZIDA] Nadjeno oglasa na strani: {len(urls)}")

        if not urls:
            print("[4ZIDA] Nema URL-ova, prekid.")
            conn.commit()
            break

        new_urls_on_page = 0
        stop_early       = False

        for i, url in enumerate(urls, start=1):
            if url in seen_urls:
                continue
            seen_urls.add(url)

            try:
                oglas_id = extract_oglas_id(url, "z4ida")

                if mode == "daily" and oglas_id_exists(cursor, oglas_id, "z4ida"):
                    consecutive_existing += 1
                    print(f"  [{i}/{len(urls)}] [4ZIDA] Postoji ({consecutive_existing}/{MAX_CONSECUTIVE_DUPLICATES}): {url}")
                    if consecutive_existing >= MAX_CONSECUTIVE_DUPLICATES:
                        print(f"  [4ZIDA] {MAX_CONSECUTIVE_DUPLICATES} uzastopna duplikata — zaustavljam.")
                        stop_early = True
                        break
                    continue

                consecutive_existing = 0
                new_urls_on_page += 1

                item = scrape_listings(context, url)
                if item is None:
                    continue
                
                item["oglas_id"] = oglas_id
                try:
                     insert_raw_row_4zida(cursor, item)
                except Exception:
                    conn.rollback()
                    conn, cursor = ensure_connection(conn, cursor, get_scraping_db_connection_params)
                    insert_raw_row_4zida(cursor, item)

                item = preprocess(item)
                if item is None:
                    continue

                if duplicate_exists(cursor, item.get("title"), item.get("price_total"), 
                                    item.get("kvadratura"), "z4ida"):
                    print(f"  [{i}/{len(urls)}] [Z4IDA] Duplikat (title+cena+kv): {url}")
                    continue

                if inserted_count > 0 and inserted_count % 50 == 0:
                    conn, cursor = ensure_connection(conn, cursor, get_scraping_db_connection_params)

                try:
                    insert_row_4zida(cursor, item)
                except Exception:
                    conn.rollback()
                    conn, cursor = ensure_connection(conn, cursor, get_scraping_db_connection_params)
                    insert_row_4zida(cursor, item)

                inserted_count += 1
                print(f"  [{i}/{len(urls)}] [4ZIDA] INSERT: {url}")

                if inserted_count % 5 == 0:
                    conn.commit()
                    print(f"  [COMMIT] INSERT={inserted_count}")

            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                print(f"[4ZIDA] Greska za {url}: {e}")

        if stop_early:
            print(f"[4ZIDA] Early stop — svi novi oglasi skrejpovani.")
            conn.commit()
            break

        if new_urls_on_page == 0:
            pages_without_new_url += 1
            print(f"[4ZIDA] Strana bez novih URL-ova ({pages_without_new_url}/{max_pages_without_new_url})")
        else:
            pages_without_new_url = 0

        if pages_without_new_url >= max_pages_without_new_url:
            print("[4ZIDA] Pet strana zaredom bez novih oglasa, prekid.")
            conn.commit()
            break

        if max_pages is not None and current_page_num >= max_pages:
            print("[4ZIDA] Dostignut max_pages limit")
            conn.commit()
            break

        if current_page_num >= hard_max_pages:
            print("Safety stop: dostignut hard_max_pages.")
            conn.commit()
            break

        current_page_num += 1
        current_url = f"https://www.4zida.rs/prodaja-stanova/beograd?sortiranje=najnoviji&strana={current_page_num}"

    conn.commit()
    print(f"\n[4ZIDA] ZAVRSENO — INSERT={inserted_count}")


def run_4zida(max_pages=None, mode="daily"):
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
            browser = p.chromium.launch(headless=True, slow_mo=150)
            context = browser.new_context(**get_context_kwargs())
            context.route("**/*", block_resources)
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            listing_page = context.new_page()
            # Sortiranje od najnovijih
            start_url = "https://www.4zida.rs/prodaja-stanova/beograd?sortiranje=najnoviji"

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
        print(f"Greska u 4zida: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()