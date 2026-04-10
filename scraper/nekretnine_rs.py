from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
from datetime import datetime
import psycopg2
from database.db_config import get_scraping_db_connection_params,ensure_connection
from database.insert_row import insert_row_nekretnine
import random
from preprocesing.pipeline import preprocess
from scraper.user_agents import get_context_kwargs

BASE_URL = "https://www.nekretnine.rs/"

FAILED_LOG_FILE = "NEKRETNINE_failed_pages_V02.txt"
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

def scrape_listings(context,url):
    page = context.new_page()
    data = {col: None for col in CSV_COLUMNS}
    data["url"] = url

    try:
        page.goto(url,wait_until="domcontentloaded")
        human_delay(page)


        #naslov
        data["title"] = protect_data(
            page.locator("h1.detail-title"),
            "title",
            url,
            timeout=2000
        )

        #Ukupna cena
        data["price_total"] = protect_data(
            page.locator("h4.stickyBox__price"),
            "price_total",
            url,
            timeout=2000
        )

        # cena po kvadratu
        data['price_per_m2'] = protect_data(page.locator("h4.stickyBox__price span"),"price_per_m2",url)
        
        # gornji blok: Tip nekretnine / Kvadratura / Broj soba
        try:
            details_section = page.locator("section#detalji")
            amenity_blocks = details_section.locator("div.property__amenities")
            block_count = amenity_blocks.count()
            for i in range(block_count):
                try:
                    block = amenity_blocks.nth(i)

                    items = block.locator("li")
                    raw_features = []
                    item_count = items.count()

                    for j in range(item_count):
                        try:
                            li = items.nth(j)
                            strong = li.locator("strong")

                            if strong.count() > 0:
                                full_text = protect_data(li, f"detail_li_{i}_{j}", url, timeout=1500)
                                field_value = protect_data(strong, f"detail_strong_{i}_{j}", url, timeout=1500)

                                if not full_text or not field_value:
                                    continue
                                
                                raw_field_name = full_text.split(":")[0].strip()
                                field_name = FIELD_MAP.get(raw_field_name, raw_field_name)

                                if field_name in data:
                                    data[field_name] = field_value
                            else:
                                feature = protect_data(li,f"feature_li_{i}_{j}",url)
                                
                                if feature:
                                    raw_features.append(feature)
                        except Exception as e:
                            save_failed_page(url,error_message=str(e))
                    try:
                        map_features(raw_features, data)
                    except Exception as e:
                        save_failed_page(url,error_message=str(e))
                except Exception as e:
                    save_failed_page(url,error_message=str(e))
        except Exception as e:
            save_failed_page(url,error_message=str(e))

        #datum_objave
        try:
            raw_datum = protect_data(page.locator("div.updated span").nth(1),"Datum_objave",url)

            if raw_datum.startswith("Objavljen:"):
                data["Datum_objave"] = raw_datum.replace("Objavljen:", "").strip()
            else:
                data["Datum_objave"] = raw_datum.strip()
        except Exception as e:
            save_failed_page(url,error_message=str(e))

        #dodatni opis
        try:
            opis_oglasa = protect_data(page.locator("section#opis .cms-content-inner"),"Dodatni_opis",url)
            if opis_oglasa:
                data["Dodatni opis"] = " ".join(opis_oglasa.split())
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


def scrape_all_pages(listing_page,context,start_url,cursor,conn,max_pages = None):
    current_url = start_url
    current_page_num = 1
    seen_urls = set()
    inserted_count = 0

    max_pages_without_new_url = 5
    pages_without_new_url = 0
    hard_max_pages = 1000

    while True:
        print(f"\n[NEKRETNINE] Obradjujem listing stranu {current_page_num}: {current_url}")
        listing_page.goto(current_url,wait_until = 'domcontentloaded')
        human_delay(listing_page)

        urls = get_listings_url(listing_page)
        print(f"[NEKRETNINE] Nadjeno oglasa na strani: {len(urls)}")
        if not urls:
            print("[NEKRETNINE] Nema URL-ova, prekid.")
            conn.commit()
            break

        new_urls_on_page = 0
        for i,url in enumerate(urls,start = 1):
            if url in seen_urls:
                continue
            seen_urls.add(url)
            new_urls_on_page +=1

            try:
                item =scrape_listings(context,url)
                if item is None:
                    continue

                item= preprocess(item)
                if item is None:
                    continue
                
                if inserted_count > 0 and inserted_count % 50 == 0:
                    conn, cursor = ensure_connection(conn, cursor, get_scraping_db_connection_params)
                try:
                    insert_row_nekretnine(cursor,item)
                except Exception:
                    conn.rollback()
                    conn,cursor = ensure_connection(conn,cursor,get_scraping_db_connection_params)
                    insert_row_nekretnine(cursor,item)

                inserted_count +=1
                if inserted_count > 0 and inserted_count % 20 == 0:
                    conn.commit()

                print(f"  [{i}/{len(urls)}] [NEKRETNINE] Sacuvan: {url}")
            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                print(f"Greska za {url}:{e}")

        if new_urls_on_page == 0:
            pages_without_new_url +=1
            print(f"[NEKRETNINE] Strana bez novih URL-ova ({pages_without_new_url}/{max_pages_without_new_url})")
        else:
            pages_without_new_url = 0
        
        if pages_without_new_url >= max_pages_without_new_url:
            print("[NEKRETNINE] Pet strana zaredom bez novih oglasa, prekid.")
            conn.commit()
            break

        if max_pages is not None and current_page_num >=max_pages:
            print("[NEKRETNINE] Dostignut max_pages limit")
            break

        if current_page_num >= hard_max_pages:
            print("Safety stop: dostignut max_pages.")
            conn.commit()
            break
            
       
        current_page_num +=1
        current_url = f"https://www.nekretnine.rs/stambeni-objekti/stanovi/izdavanje-prodaja/prodaja/grad/beograd/lista/po-stranici/10/stranica/{current_page_num}"
    conn.commit()

def run_nekretnine(max_pages = 3):
    conn = None
    cursor = None

    try:
        conn = psycopg2.connect(
            **get_scraping_db_connection_params(),
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5)
        
        cursor = conn.cursor()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True,slow_mo=100)

            context = browser.new_context(**get_context_kwargs())
            context.route("**/*", block_resources)

            context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            """)

            listing_page = context.new_page()
            #details_page = context.new_page()

            start_url = "https://www.nekretnine.rs/stambeni-objekti/stanovi/izdavanje-prodaja/prodaja/grad/beograd/lista/po-stranici/10/"


            scrape_all_pages(
                        listing_page=listing_page,
                        context=context,
                        start_url=start_url,
                        cursor=cursor,
                        conn=conn,
                        max_pages=max_pages
                    )
            

            listing_page.close()
            #details_page.close()
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

