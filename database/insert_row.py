import psycopg2
from .db_config import get_scraping_db_connection_params

REQUIRED_FIELDS = [
    "datum_objave",
    "title",
    "price_total",
    "price_per_m2",
    "kvadratura",
    "sprat",
    "broj_soba",
]

def _build_params(item: dict) -> dict:
    return {
        "url":                      item.get("url"),
        "oglas_id":                 item.get("oglas_id"),
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
        "lokacija":                 item.get("lokacija"),
    }


def _insert_query(table: str) -> str:
    return f"""
        INSERT INTO public.{table} (
            url,oglas_id ,title, price_total, price_per_m2,
            tip_nekretnine, kvadratura, broj_soba, oglasivac,
            tip_objekta, stanje_objekta, grejanje, sprat,
            ukupna_spratnost, uknjizen, terasa, interfon,
            klima, video_nadzor, internet, parking, garaza,
            lift, podrum, linije_gradskog_prevoza,
            datum_objave, dodatni_opis,lokacija
        )
        VALUES (
            %(url)s,%(oglas_id)s, %(title)s, %(price_total)s, %(price_per_m2)s,
            %(tip_nekretnine)s, %(kvadratura)s, %(broj_soba)s, %(oglasivac)s,
            %(tip_objekta)s, %(stanje_objekta)s, %(grejanje)s, %(sprat)s,
            %(ukupna_spratnost)s, %(uknjizen)s, %(terasa)s, %(interfon)s,
            %(klima)s, %(video_nadzor)s, %(internet)s, %(parking)s, %(garaza)s,
            %(lift)s, %(podrum)s, %(linije_gradskog_prevoza)s,
            %(datum_objave)s, %(dodatni_opis)s, %(lokacija)s
        )
        ON CONFLICT (oglas_id) DO UPDATE SET
            url                     = EXCLUDED.url,
            title                   = COALESCE(NULLIF({table}.title, ''),                   NULLIF(EXCLUDED.title, '')),
            price_total             = COALESCE({table}.price_total,             EXCLUDED.price_total),
            price_per_m2            = COALESCE({table}.price_per_m2,            EXCLUDED.price_per_m2),
            tip_nekretnine          = COALESCE(NULLIF({table}.tip_nekretnine, ''),          NULLIF(EXCLUDED.tip_nekretnine, '')),
            kvadratura              = COALESCE({table}.kvadratura,              EXCLUDED.kvadratura),
            broj_soba               = COALESCE({table}.broj_soba,               EXCLUDED.broj_soba),
            oglasivac               = COALESCE(NULLIF({table}.oglasivac, ''),               NULLIF(EXCLUDED.oglasivac, '')),
            tip_objekta             = COALESCE(NULLIF({table}.tip_objekta, ''),             NULLIF(EXCLUDED.tip_objekta, '')),
            stanje_objekta          = COALESCE(NULLIF({table}.stanje_objekta, ''),          NULLIF(EXCLUDED.stanje_objekta, '')),
            grejanje                = COALESCE(NULLIF({table}.grejanje, ''),                NULLIF(EXCLUDED.grejanje, '')),
            sprat                   = COALESCE({table}.sprat,                   EXCLUDED.sprat),
            ukupna_spratnost        = COALESCE({table}.ukupna_spratnost,        EXCLUDED.ukupna_spratnost),
            uknjizen                = COALESCE({table}.uknjizen,                EXCLUDED.uknjizen),
            terasa                  = COALESCE({table}.terasa,                  EXCLUDED.terasa),
            interfon                = COALESCE({table}.interfon,                EXCLUDED.interfon),
            klima                   = COALESCE({table}.klima,                   EXCLUDED.klima),
            video_nadzor            = COALESCE({table}.video_nadzor,            EXCLUDED.video_nadzor),
            internet                = COALESCE({table}.internet,                EXCLUDED.internet),
            parking                 = COALESCE({table}.parking,                 EXCLUDED.parking),
            garaza                  = COALESCE({table}.garaza,                  EXCLUDED.garaza),
            lift                    = COALESCE({table}.lift,                    EXCLUDED.lift),
            podrum                  = COALESCE({table}.podrum,                  EXCLUDED.podrum),
            linije_gradskog_prevoza = COALESCE(NULLIF({table}.linije_gradskog_prevoza, ''), NULLIF(EXCLUDED.linije_gradskog_prevoza, '')),
            datum_objave            = COALESCE({table}.datum_objave,            EXCLUDED.datum_objave),
            dodatni_opis            = COALESCE(NULLIF({table}.dodatni_opis, ''),            NULLIF(EXCLUDED.dodatni_opis, '')),
            "lokacija"              = COALESCE(NULLIF({table}."lokacija", 'Nepoznato'), NULLIF(EXCLUDED."lokacija", 'Nepoznato'));
    """


def _update_query(table: str) -> str:
    return f"""
        UPDATE {table}
        SET
            title                   = COALESCE({table}.title,                   %(title)s),
            price_total             = COALESCE({table}.price_total,             %(price_total)s),
            price_per_m2            = COALESCE({table}.price_per_m2,            %(price_per_m2)s),
            tip_nekretnine          = COALESCE({table}.tip_nekretnine,          %(tip_nekretnine)s),
            kvadratura              = COALESCE({table}.kvadratura,              %(kvadratura)s),
            broj_soba               = COALESCE({table}.broj_soba,               %(broj_soba)s),
            oglasivac               = COALESCE({table}.oglasivac,               %(oglasivac)s),
            tip_objekta             = COALESCE({table}.tip_objekta,             %(tip_objekta)s),
            stanje_objekta          = COALESCE({table}.stanje_objekta,          %(stanje_objekta)s),
            grejanje                = COALESCE({table}.grejanje,                %(grejanje)s),
            sprat                   = COALESCE({table}.sprat,                   %(sprat)s),
            ukupna_spratnost        = COALESCE({table}.ukupna_spratnost,        %(ukupna_spratnost)s),
            uknjizen                = COALESCE({table}.uknjizen,                %(uknjizen)s),
            terasa                  = COALESCE({table}.terasa,                  %(terasa)s),
            interfon                = COALESCE({table}.interfon,                %(interfon)s),
            klima                   = COALESCE({table}.klima,                   %(klima)s),
            video_nadzor            = COALESCE({table}.video_nadzor,            %(video_nadzor)s),
            internet                = COALESCE({table}.internet,                %(internet)s),
            parking                 = COALESCE({table}.parking,                 %(parking)s),
            garaza                  = COALESCE({table}.garaza,                  %(garaza)s),
            lift                    = COALESCE({table}.lift,                    %(lift)s),
            podrum                  = COALESCE({table}.podrum,                  %(podrum)s),
            linije_gradskog_prevoza = COALESCE({table}.linije_gradskog_prevoza, %(linije_gradskog_prevoza)s),
            datum_objave            = COALESCE({table}.datum_objave,            %(datum_objave)s),
            dodatni_opis            = COALESCE({table}.dodatni_opis,            %(dodatni_opis)s),
            "lokacija"              = COALESCE(NULLIF({table}."lokacija", 'Nepoznato'), %(lokacija)s)
        WHERE {table}.oglas_id = %(oglas_id)s;
    """

def fetch_urls_to_update(cursor, table: str) -> list[str]:
    """
    Vraca URL-ove redova gde bar jedna od REQUIRED_FIELDS kolona je NULL.
    
    Args:
        cursor: DB kursor
        table:  ime tabele — 'halo_oglasi', 'z4ida' ili 'nekretnine_rs'
    """
    conditions = " OR ".join(f"{f} IS NULL" for f in REQUIRED_FIELDS)
    query = f"""
        SELECT url
        FROM {table}
        WHERE {conditions}
        ORDER BY id ASC;
    """
    cursor.execute(query)
    return [row[0] for row in cursor.fetchall() if row[0]]

def insert_row_halo(cursor, item: dict) -> None:
    cursor.execute(_insert_query("halo_oglasi"), _build_params(item))

def insert_row_4zida(cursor, item: dict) -> None:
    cursor.execute(_insert_query("z4ida"), _build_params(item))

def insert_row_nekretnine(cursor, item: dict) -> None:
    cursor.execute(_insert_query("nekretnine_rs"), _build_params(item))

def update_full_row_halo(cursor, item: dict) -> int:
    """Vraca broj azuriranih redova (0 ili 1)."""
    cursor.execute(_update_query("halo_oglasi"), _build_params(item))
    return cursor.rowcount
 
 
def update_full_row_4zida(cursor, item: dict) -> int:
    """Vraca broj azuriranih redova (0 ili 1)."""
    cursor.execute(_update_query("z4ida"), _build_params(item))
    return cursor.rowcount
 
 
def update_full_row_nekretnine(cursor, item: dict) -> int:
    """Vraca broj azuriranih redova (0 ili 1)."""
    cursor.execute(_update_query("nekretnine_rs"), _build_params(item))
    return cursor.rowcount


def update_missing_halo_listing_only_by_url(cursor, item):
    query = """
    UPDATE halo_oglasi
    SET
        title            = COALESCE(halo_oglasi.title,            %(title)s),
        price_total      = COALESCE(halo_oglasi.price_total,      %(price_total)s),
        price_per_m2     = COALESCE(halo_oglasi.price_per_m2,     %(price_per_m2)s),
        kvadratura       = COALESCE(halo_oglasi.kvadratura,       %(kvadratura)s),
        broj_soba        = COALESCE(halo_oglasi.broj_soba,        %(broj_soba)s),
        sprat            = COALESCE(halo_oglasi.sprat,            %(sprat)s),
        ukupna_spratnost = COALESCE(halo_oglasi.ukupna_spratnost, %(ukupna_spratnost)s),
        datum_objave     = COALESCE(halo_oglasi.datum_objave,     %(datum_objave)s)
    WHERE halo_oglasi.url = %(url)s
      AND (
          halo_oglasi.title        IS NULL OR
          halo_oglasi.price_total  IS NULL OR
          halo_oglasi.price_per_m2 IS NULL OR
          halo_oglasi.kvadratura   IS NULL OR
          halo_oglasi.broj_soba    IS NULL OR
          halo_oglasi.sprat        IS NULL OR
          halo_oglasi.ukupna_spratnost IS NULL OR
          halo_oglasi.datum_objave IS NULL
      );
    """
    cursor.execute(query, _build_params(item))