import re
from urllib.parse import urljoin
import time
import random

import psycopg2
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from preprocesing.pipeline import preprocess
from database.db_config import get_scraping_db_connection_params
from scraper.user_agents import get_context_kwargs


def update_missing_halo_listing_only_by_url(cursor, item):
    query = """
    UPDATE halo_oglasi
    SET
        title = COALESCE(halo_oglasi.title, %(title)s),
        price_total = COALESCE(halo_oglasi.price_total, %(price_total)s),
        price_per_m2 = COALESCE(halo_oglasi.price_per_m2, %(price_per_m2)s),
        kvadratura = COALESCE(halo_oglasi.kvadratura, %(kvadratura)s),
        broj_soba = COALESCE(halo_oglasi.broj_soba, %(broj_soba)s),
        sprat = COALESCE(halo_oglasi.sprat, CAST(%(sprat)s AS text)),
        ukupna_spratnost = COALESCE(halo_oglasi.ukupna_spratnost, %(ukupna_spratnost)s),
        datum_objave = COALESCE(halo_oglasi.datum_objave, %(datum_objave)s)
    WHERE substring(halo_oglasi.url from '/([0-9]+)(?:\\?|$)') =
          substring(%(url)s from '/([0-9]+)(?:\\?|$)')
      AND halo_oglasi.datum_objave IS NULL;
    """
    cursor.execute(query, item)


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

def txt(node):
    return node.get_text(" ", strip=True) if node else None

def human_pause(min_s=0.8, max_s=2.0):
    time.sleep(random.uniform(min_s, max_s))

def normalize_floor_value(raw_floor):
    if raw_floor is None:
        return None

    s = str(raw_floor).strip().lower()

    roman_map = {
        "pr": "prizemlje",
        "p": "prizemlje",
        "vpr": "visoko prizemlje",
        "vp": "visoko prizemlje",
        "sut": "suteren",
        "su": "suteren",
        "psut": "suteren",
        "i": "1",
        "ii": "2",
        "iii": "3",
        "iv": "4",
        "v": "5",
        "vi": "6",
        "vii": "7",
        "viii": "8",
        "ix": "9",
        "x": "10",
        "xi": "11",
        "xii": "12",
        "xiii": "13",
        "xiv": "14",
        "xv": "15",
    }

    return roman_map.get(s, raw_floor)

def close_halo_popups(page):
    try:
        popup_button = page.locator("button:has-text('U redu'), input[value='U redu'], a:has-text('U redu')")
        if popup_button.count() > 0:
            popup_button.first.click(timeout=2000)
            page.wait_for_timeout(1000)
    except Exception:
        pass

def extract_floor_and_total(raw_value):
    if not raw_value:
        return None, None

    value = str(raw_value).strip()

    if "/" in value:
        sprat_raw, ukupno_raw = value.split("/", 1)
        return normalize_floor_value(sprat_raw.strip()), ukupno_raw.strip()

    return normalize_floor_value(value), None


def parse_halo_listing_card(card, base_url="https://www.halooglasi.com"):
    item = {
        "id": None,
        "url": None,
        "title": None,
        "price_total": None,
        "price_per_m2": None,
        "Kvadratura": None,
        "Broj soba": None,
        "Sprat": None,
        "Ukupna spratnost": None,
        "Datum_objave": None,
        "Tip nekretnine": "stan",
        "Dodatni opis": None,
        "Tip objekta": None,
        "Stanje objekta": None,
        "Grejanje": None,
        "Uknjižen": None,
        "Terasa": None,
        "Interfon": None,
        "Klima": None,
        "Video nadzor": None,
        "Internet": None,
        "Parking": None,
        "Garaža": None,
        "Lift": None,
        "Podrum": None,
    }

    item["id"] = card.get("data-id") or card.get("id")

    title_a = card.select_one("h3.product-title a")
    if title_a:
        item["title"] = txt(title_a)
        href = title_a.get("href")
        if href:
            item["url"] = urljoin(base_url, href)

    price_total_el = card.select_one(".central-feature span[data-value]")
    if price_total_el:
        item["price_total"] = price_total_el.get("data-value") or txt(price_total_el)

    price_per_m2_el = card.select_one(".price-by-surface span")
    if price_per_m2_el:
        item["price_per_m2"] = txt(price_per_m2_el)

    publish_date_el = card.select_one(".publish-date")
    if publish_date_el:
        item["Datum_objave"] = txt(publish_date_el)

    desc_el = card.select_one("p.product-description, p.text-description-list, p.short-desc")
    if desc_el:
        item["Dodatni opis"] = txt(desc_el)

    for li in card.select("ul.product-features li"):
        legend_el = li.select_one(".legend")
        wrapper_el = li.select_one(".value-wrapper")

        if not legend_el or not wrapper_el:
            continue

        legend = txt(legend_el)
        full_value = txt(wrapper_el)

        if not legend or not full_value:
            continue

        value = full_value.replace(legend, "").strip()

        if legend == "Kvadratura":
            item["Kvadratura"] = value

        elif legend == "Broj soba":
            item["Broj soba"] = value

        elif legend == "Spratnost":
            sprat, ukupna_spratnost = extract_floor_and_total(value)
            item["Sprat"] = sprat
            item["Ukupna spratnost"] = ukupna_spratnost

    return item


def parse_halo_listing_page_html(html, base_url="https://www.halooglasi.com"):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.product-item.product-list-item[data-id]")
    items = []

    for card in cards:
        try:
            item = parse_halo_listing_card(card, base_url=base_url)
            if item.get("url"):
                items.append(item)
            
        except Exception as e:
            print(f"[HALO] Greška pri parsiranju kartice: {e}")

    return items


def build_next_page_url(page_number):
    return f"https://www.halooglasi.com/nekretnine/prodaja-stanova/beograd?page={page_number}"


def scrape_and_update_halo_listings(max_pages=3, headless=False):
    conn = None
    cursor = None
    browser = None
    context = None
    listing_page = None

    total_seen = 0
    total_updated = 0
    total_failed = 0

    try:
        conn = psycopg2.connect(
            **get_scraping_db_connection_params(),
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
        )
        cursor = conn.cursor()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, slow_mo=150)

            context = browser.new_context(**get_context_kwargs())
            context.route("**/*", block_resources)

            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            listing_page = context.new_page()
            listing_page.set_default_timeout(90000)

            page_num = 1

            while True:
                if max_pages is not None and page_num > max_pages:
                    break
                url = build_next_page_url(page_num)
                print(f"\n[HALO] Obradjujem listing stranu {page_num}: {url}")

                try:
                    human_pause(0.8, 1.8)
                    listing_page.goto(url, wait_until="domcontentloaded", timeout=90000)
                    close_halo_popups(listing_page)
                    listing_page.wait_for_selector(
                        "div.product-item.product-list-item[data-id]",
                        timeout=30000
                    )
                except PlaywrightTimeoutError:
                    print(f"[HALO] Timeout na listing strani {page_num}")
                    total_failed += 1
                    break
                except Exception as e:
                    print(f"[HALO] Greska pri ucitavanju listing strane {page_num}: {e}")
                    total_failed += 1
                    continue

                html = listing_page.content()
                raw_items = parse_halo_listing_page_html(html)

                print(f"[HALO] Nadjeno oglasa na strani: {len(raw_items)}")

                if not raw_items:
                    print("[HALO] Nema vise oglasa ili se HTML promenio.")
                    break

                page_updated = 0

                for raw_item in raw_items:
                    total_seen += 1

                    try:

                        cleaned_item = preprocess(raw_item)

                        db_item = {
                            "id": cleaned_item.get("id"),
                            "url": cleaned_item.get("url"),
                            "title": cleaned_item.get("title"),
                            "price_total": cleaned_item.get("price_total"),
                            "price_per_m2": cleaned_item.get("price_per_m2"),
                            "kvadratura": cleaned_item.get("Kvadratura"),
                            "broj_soba": cleaned_item.get("Broj soba"),
                            "sprat": cleaned_item.get("Sprat"),
                            "ukupna_spratnost": cleaned_item.get("Ukupna spratnost"),
                            "datum_objave": cleaned_item.get("Datum_objave"),
                        }

                        if not db_item["url"]:
                            print("[HALO] Preskacem oglas bez URL-a.")
                            continue

                        update_missing_halo_listing_only_by_url(cursor, db_item)

                        #print("PARSED DATUM:", raw_item.get("Datum_objave"))
                        #print("CLEANED DATUM:", cleaned_item.get("Datum_objave"))
                        #print("DB DATUM:", db_item.get("datum_objave"))
                        if cursor.rowcount > 0:
                            page_updated += 1
                            total_updated += 1
                            print(
                                f"[HALO] UPDATE OK | "
                                f"url={db_item['url']} | "
                                f"title={db_item['title']}"
                            )

                    except Exception as e:
                        total_failed += 1
                        print(f"[HALO] Greska za {raw_item.get('url')}: {e}")
                        conn.rollback()
                        continue

                conn.commit()
                print(f"[HALO] Strana {page_num} zavrsena. Updated: {page_updated}")
                page_num += 1

            print("\n[HALO] ZAVRSENO")
            print(f"[HALO] Ukupno vidjeno: {total_seen}")
            print(f"[HALO] Ukupno update-ovano: {total_updated}")
            print(f"[HALO] Ukupno gresaka: {total_failed}")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[HALO] Glavna greska: {e}")

    finally:
        try:
            if listing_page:
                listing_page.close()
        except Exception:
            pass

        try:
            if context:
                context.close()
        except Exception:
            pass

        try:
            if browser:
                browser.close()
        except Exception:
            pass

        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    scrape_and_update_halo_listings(max_pages=None, headless=False)