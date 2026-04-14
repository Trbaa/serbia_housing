"""
halo_full_update_v2.py

Čita URL-ove iz baze gde nedostaju podaci,
otvara svaki oglas direktno i radi kompletan UPDATE svih polja.
Koristi iste user-agente, headers i human_delay kao halo_oglasi.py.
"""

import random
from datetime import datetime

import psycopg2
from playwright.sync_api import sync_playwright

from database.db_config import get_scraping_db_connection_params, ensure_connection
from preprocesing.pipeline import preprocess
from scraper.user_agents import get_context_kwargs


# --------------------------------------------------------------------------- #
# Konfiguracija
# --------------------------------------------------------------------------- #

FAILED_LOG_FILE = "HALO_full_update_v2_failed.txt"

REQUIRED_FIELDS = [
    "datum_objave",
    "price_total",
    "price_per_m2",
    "broj_soba",
    "sprat",
    "ukupna_spratnost",
]

CSV_COLUMNS = [
    "url", "title", "price_total", "price_per_m2",
    "Tip nekretnine", "Kvadratura", "Broj soba", "Oglašivač",
    "Tip objekta", "Stanje objekta", "Grejanje", "Sprat",
    "Ukupna spratnost", "Uknjižen", "Terasa", "Interfon",
    "Klima", "Video nadzor", "Internet", "Parking", "Garaža",
    "Lift", "Podrum", "Linije gradskog prevoza",
    "Datum_objave", "Dodatni opis",
]


# --------------------------------------------------------------------------- #
# Pomoćne funkcije — identične kao u halo_oglasi.py
# --------------------------------------------------------------------------- #

def save_failed_page(url: str, error_message: str) -> None:
    with open(FAILED_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"
            f" URL: {url} | ERROR: {error_message}\n"
        )


def block_resources(route) -> None:
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


def close_halo_popups(page) -> None:
    try:
        popup_button = page.locator(
            "button:has-text('U redu'), input[value='U redu'], a:has-text('U redu')"
        )
        if popup_button.count() > 0:
            popup_button.first.click(timeout=2000)
            page.wait_for_timeout(1000)
    except Exception:
        pass


def human_delay(page, a: int = 800, b: int = 8000) -> None:
    page.wait_for_timeout(random.randint(a, b))


def protect_data(locator, field_name: str, url: str, timeout: int = 3000):
    try:
        if locator.count() == 0:
            return None
        text = locator.first.inner_text(timeout=timeout)
        return text.strip() if text else None
    except Exception as e:
        save_failed_page(url, f"{field_name}: {e}")
        return None


# --------------------------------------------------------------------------- #
# Učitavanje URL-ova iz baze
# --------------------------------------------------------------------------- #

def fetch_urls_to_update(cursor) -> list[str]:
    conditions = " OR ".join(f"{f} IS NULL" for f in REQUIRED_FIELDS)
    query = f"""
        SELECT url
        FROM halo_oglasi
        WHERE {conditions}
        ORDER BY id ASC;
    """
    cursor.execute(query)
    return [row[0] for row in cursor.fetchall() if row[0]]


# --------------------------------------------------------------------------- #
# Scrape jednog oglasa — identično kao u halo_oglasi.py
# --------------------------------------------------------------------------- #

def scrape_listing(context, url: str) -> dict | None:
    page = context.new_page()
    human_delay(page)
    data = {col: None for col in CSV_COLUMNS}
    data["url"] = url

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        close_halo_popups(page)
        page.wait_for_selector("h1", state="attached", timeout=15000)
        page.wait_for_timeout(1500)

        # Naslov
        data["title"] = protect_data(page.locator("h1"), "title", url)

        # Cene
        data["price_total"] = protect_data(
            page.locator("span[data-value]"), "price_total", url
        )
        data["price_per_m2"] = protect_data(
            page.locator("div.price-by-surface span"), "price_per_m2", url
        )

        # Gornji blok: Tip nekretnine / Kvadratura / Broj soba
        try:
            prominent_items = page.locator("div.prominent li")
            for i in range(prominent_items.count()):
                try:
                    item = prominent_items.nth(i)
                    fn = item.locator("span.field-name")
                    fv = item.locator("span.field-value")
                    if fn.count() == 0 or fv.count() == 0:
                        continue
                    key = fn.first.inner_text().strip()
                    val = fv.first.inner_text().strip()
                    if key in data:
                        data[key] = val
                except Exception as e:
                    save_failed_page(url, f"prominent item {i}: {e}")
        except Exception as e:
            save_failed_page(url, f"prominent block: {e}")

        # Desni datasheet blok
        try:
            detail_rows = page.locator(
                "div.datasheet.product-basic-details div.basic-view"
            )
            for i in range(detail_rows.count()):
                try:
                    row = detail_rows.nth(i)
                    cols = row.locator("div.row > div")
                    if cols.count() < 2:
                        continue
                    key = cols.nth(0).inner_text().strip()
                    val = cols.nth(1).inner_text().strip()
                    if key in data:
                        data[key] = val
                except Exception as e:
                    save_failed_page(url, f"datasheet row {i}: {e}")
        except Exception as e:
            save_failed_page(url, f"datasheet block: {e}")

        # Dodatno + Ostalo (boolean polja)
        for section_name in ["Dodatno", "Ostalo"]:
            try:
                section_block = page.locator(
                    f"div.tab-attribute:has(div.tab-section-header label:text-is('{section_name}'))"
                )
                if section_block.count() == 0:
                    continue
                feature_labels = section_block.locator(
                    "div.flags-container span.flag-attribute label"
                )
                for i in range(feature_labels.count()):
                    try:
                        feature_name = protect_data(
                            feature_labels.nth(i), f"{section_name}_feature_{i}", url
                        )
                        if feature_name and feature_name in data:
                            data[feature_name] = "da"
                    except Exception as e:
                        save_failed_page(url, f"{section_name} feature {i}: {e}")
            except Exception as e:
                save_failed_page(url, f"{section_name} block: {e}")

        # Linije gradskog prevoza
        try:
            transport_block = page.locator("div.city-lines")
            if transport_block.count() > 0:
                lines = []
                for i in range(transport_block.locator("ul li").count()):
                    try:
                        line_text = protect_data(
                            transport_block.locator("ul li").nth(i),
                            f"line_item_{i}", url
                        )
                        if line_text:
                            lines.append(line_text)
                    except Exception as e:
                        save_failed_page(url, f"transport item {i}: {e}")
                if lines:
                    data["Linije gradskog prevoza"] = ", ".join(lines)
        except Exception as e:
            save_failed_page(url, f"transport block: {e}")

        # Datum objave — identično kao u halo_oglasi.py
        try:
            date_row = page.locator("div.line", has_text="Objavljen")
            data["Datum_objave"] = protect_data(
                date_row.locator("span.value strong"),
                "Datum_objave",
                url,
                timeout=3000,
            )
            # Fallback — probaj širi selector ako prvi ne uhvati
            if data["Datum_objave"] is None:
                data["Datum_objave"] = protect_data(
                    page.locator("span.value strong").first,
                    "Datum_objave_fallback",
                    url,
                    timeout=2000,
                )
        except Exception as e:
            save_failed_page(url, f"datum block: {e}")

        # Dodatni opis
        try:
            description_block = page.locator(
                "div.tab-attribute:has(div.tab-section-header label:text-is('Dodatni opis'))"
            )
            if description_block.count() > 0:
                description_text = protect_data(
                    description_block.locator("div.tab-top-group-attr-value span"),
                    "Dodatni_opis", url
                )
                if description_text:
                    data["Dodatni opis"] = " ".join(description_text.split())
        except Exception as e:
            save_failed_page(url, f"opis block: {e}")

        return data

    except Exception as e:
        save_failed_page(url, str(e))
        return None
    finally:
        try:
            page.close()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# UPDATE u bazi — sva polja, COALESCE čuva postojeće vrednosti
# --------------------------------------------------------------------------- #

def update_full_row(cursor, item: dict) -> int:
    query = """
        UPDATE halo_oglasi
        SET
            title                   = COALESCE(halo_oglasi.title,                   %(title)s),
            price_total             = COALESCE(halo_oglasi.price_total,             %(price_total)s),
            price_per_m2            = COALESCE(halo_oglasi.price_per_m2,            %(price_per_m2)s),
            tip_nekretnine          = COALESCE(halo_oglasi.tip_nekretnine,          %(tip_nekretnine)s),
            kvadratura              = COALESCE(halo_oglasi.kvadratura,              %(kvadratura)s),
            broj_soba               = COALESCE(halo_oglasi.broj_soba,               %(broj_soba)s),
            oglasivac               = COALESCE(halo_oglasi.oglasivac,               %(oglasivac)s),
            tip_objekta             = COALESCE(halo_oglasi.tip_objekta,             %(tip_objekta)s),
            stanje_objekta          = COALESCE(halo_oglasi.stanje_objekta,          %(stanje_objekta)s),
            grejanje                = COALESCE(halo_oglasi.grejanje,                %(grejanje)s),
            sprat                   = COALESCE(halo_oglasi.sprat,                   %(sprat)s),
            ukupna_spratnost        = COALESCE(halo_oglasi.ukupna_spratnost,        %(ukupna_spratnost)s),
            uknjizen                = COALESCE(halo_oglasi.uknjizen,                %(uknjizen)s),
            terasa                  = COALESCE(halo_oglasi.terasa,                  %(terasa)s),
            interfon                = COALESCE(halo_oglasi.interfon,                %(interfon)s),
            klima                   = COALESCE(halo_oglasi.klima,                   %(klima)s),
            video_nadzor            = COALESCE(halo_oglasi.video_nadzor,            %(video_nadzor)s),
            internet                = COALESCE(halo_oglasi.internet,                %(internet)s),
            parking                 = COALESCE(halo_oglasi.parking,                 %(parking)s),
            garaza                  = COALESCE(halo_oglasi.garaza,                  %(garaza)s),
            lift                    = COALESCE(halo_oglasi.lift,                    %(lift)s),
            podrum                  = COALESCE(halo_oglasi.podrum,                  %(podrum)s),
            linije_gradskog_prevoza = COALESCE(halo_oglasi.linije_gradskog_prevoza, %(linije_gradskog_prevoza)s),
            datum_objave            = COALESCE(halo_oglasi.datum_objave,            %(datum_objave)s),
            dodatni_opis            = COALESCE(halo_oglasi.dodatni_opis,            %(dodatni_opis)s)
        WHERE halo_oglasi.url = %(url)s;
    """
    params = {
        "url":                      item.get("url"),
        "title":                    item.get("title"),
        "price_total":              item.get("price_total"),
        "price_per_m2":             item.get("price_per_m2"),
        "tip_nekretnine":           item.get("Tip nekretnine"),
        "kvadratura":               item.get("Kvadratura"),
        "broj_soba":                item.get("Broj soba"),
        "oglasivac":                item.get("Oglašivač"),
        "tip_objekta":              item.get("Tip objekta"),
        "stanje_objekta":           item.get("Stanje objekta"),
        "grejanje":                 item.get("Grejanje"),
        "sprat":                    item.get("Sprat"),
        "ukupna_spratnost":         item.get("Ukupna spratnost"),
        "uknjizen":                 item.get("Uknjižen"),
        "terasa":                   item.get("Terasa"),
        "interfon":                 item.get("Interfon"),
        "klima":                    item.get("Klima"),
        "video_nadzor":             item.get("Video nadzor"),
        "internet":                 item.get("Internet"),
        "parking":                  item.get("Parking"),
        "garaza":                   item.get("Garaža"),
        "lift":                     item.get("Lift"),
        "podrum":                   item.get("Podrum"),
        "linije_gradskog_prevoza":  item.get("Linije gradskog prevoza"),
        "datum_objave":             item.get("Datum_objave"),
        "dodatni_opis":             item.get("Dodatni opis"),
    }
    cursor.execute(query, params)
    return cursor.rowcount


# --------------------------------------------------------------------------- #
# Glavna funkcija
# --------------------------------------------------------------------------- #

def run_full_update(batch_commit: int = 20, headless: bool = False) -> None:
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

        urls  = fetch_urls_to_update(cursor)
        total = len(urls)
        print(f"[UPDATE] Pronađeno {total} redova za update.")

        if not total:
            print("[UPDATE] Nema posla.")
            return

        updated = 0
        skipped = 0
        failed  = 0

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless, slow_mo=150)
            context = browser.new_context(**get_context_kwargs())
            context.route("**/*", block_resources)
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            for idx, url in enumerate(urls, start=1):
                print(f"[{idx}/{total}] {url}")

                try:
                    raw = scrape_listing(context, url)

                    if raw is None:
                        print(f"  -> scrape vratio None, preskačem.")
                        skipped += 1
                        continue

                    item = preprocess(raw)

                    if item is None:
                        print(f"  -> preprocess vratio None, preskačem.")
                        skipped += 1
                        continue

                    datum = item.get("Datum_objave")
                    print(f"  -> Datum: {datum}")

                    rows = update_full_row(cursor, item)

                    if rows > 0:
                        updated += 1
                        print(f"  -> UPDATE OK ({rows} red)")
                    else:
                        skipped += 1
                        print(f"  -> URL nije nađen u bazi.")

                    if updated % batch_commit == 0 and updated > 0:
                        conn.commit()
                        print(f"  [COMMIT] {updated} updatovano do sad.")

                    if idx % 100 == 0:
                        conn, cursor = ensure_connection(
                            conn, cursor, get_scraping_db_connection_params
                        )

                except Exception as e:
                    failed += 1
                    save_failed_page(url, str(e))
                    print(f"  -> GREŠKA: {e}")
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    conn, cursor = ensure_connection(
                        conn, cursor, get_scraping_db_connection_params
                    )

            context.close()
            browser.close()

        conn.commit()
        print("\n" + "=" * 55)
        print(f"[UPDATE] ZAVRŠENO")
        print(f"[UPDATE] Ukupno URL-ova:  {total}")
        print(f"[UPDATE] Updated:         {updated}")
        print(f"[UPDATE] Preskočeno:      {skipped}")
        print(f"[UPDATE] Grešaka:         {failed}")
        print("=" * 55)

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[UPDATE] Glavna greška: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    run_full_update(batch_commit=20, headless=False)