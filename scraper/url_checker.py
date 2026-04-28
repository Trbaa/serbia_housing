import re
from database.insert_row import REQUIRED_FIELDS


URL_NEW        = "new"         # oglas_id ne postoji u bazi → INSERT
URL_COMPLETE   = "complete"    # oglas postoji, svi podaci su tu → PRESKOČI
URL_INCOMPLETE = "incomplete"  # oglas postoji, nedostaju podaci → UPDATE


import re

def extract_oglas_id(url: str, table: str) -> str | None:
    """
    Izvlači jedinstveni ID oglasa iz URL-a zavisno od sajta.

    halo_oglasi:   numerički ID, 10+ cifara  → 5425647022667
    z4ida:         hex string, 24 karaktera  → 69dfc44bf8af725eaf03ca39
    nekretnine_rs: alphanumerički, 4-20 kar  → NksEAVNuU57
                   ili numerički             → 664845
    """
    if not url:
        return None

    # Ukloni query parametre i trailing whitespace
    # npr. .../NkiuQRBNlDr/?order=2 → .../NkiuQRBNlDr/
    url = url.split("?")[0].strip()

    if table == "halo_oglasi":
        m = re.search(r'/(\d{10,})(?:/)?$', url)

    elif table == "z4ida":
        m = re.search(r'/([a-f0-9]{24})(?:/)?$', url)

    elif table == "nekretnine_rs":
        # Pokriva:
        # → novi format: NkiuQRBNlDr, Nkh10QBF-j6
        # → stari format: 664845, 1867895
        m = re.search(r'/([A-Za-z0-9_-]{4,20})(?:/)?$', url)


    else:
        return None

    return m.group(1) if m else None


def check_url_status(cursor, url: str, table: str) -> str:
    oglas_id = extract_oglas_id(url, table)
    if not oglas_id:
        return URL_NEW

    fields_select = ", ".join(REQUIRED_FIELDS)
    query = f"""
        SELECT {fields_select}
        FROM silver.{table}
        WHERE oglas_id = %s
        LIMIT 1;
    """
    cursor.execute(query, (oglas_id,))
    row = cursor.fetchone()

    if row is None:
        return URL_NEW

    has_missing = any(value is None for value in row)
    
    # Dodaj detekciju anti-bot title-a
    if table == "halo_oglasi":
        title_index = REQUIRED_FIELDS.index("title")
        title_val = row[title_index]
        if title_val and "halooglasi" in str(title_val).lower():
            return URL_INCOMPLETE

    return URL_INCOMPLETE if has_missing else URL_COMPLETE

def oglas_id_exists(cursor, oglas_id: str, table: str) -> bool:
    if not oglas_id:
        return False
 
    cursor.execute(
        f"SELECT 1 FROM silver.{table} WHERE oglas_id = %s LIMIT 1;",
        (oglas_id,)
    )
    return cursor.fetchone() is not None
 
def duplicate_exists(cursor, title: str, price_total: float, 
                     kvadratura: float, table: str) -> bool:
    if not title or not price_total or not kvadratura:
        return False
    cursor.execute(
        f"""SELECT 1 FROM silver.{table}
            WHERE title = %s 
            AND price_total = %s 
            AND kvadratura = %s 
            LIMIT 1;""",
        (title, price_total, kvadratura)
    )
    return cursor.fetchone() is not None