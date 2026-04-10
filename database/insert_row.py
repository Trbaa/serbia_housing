import psycopg2
from .db_config import get_scraping_db_connection_params


def insert_row_halo(cursor,item):
        query = """
            INSERT INTO public.halo_oglasi (
                url,
                title,
                price_total,
                price_per_m2,
                tip_nekretnine,
                kvadratura,
                broj_soba,
                oglasivac,
                tip_objekta,
                stanje_objekta,
                grejanje,
                sprat,
                ukupna_spratnost,
                uknjizen,
                terasa,
                interfon,
                klima,
                video_nadzor,
                internet,
                parking,
                garaza,
                lift,
                podrum,
                linije_gradskog_prevoza,
                datum_objave,
                dodatni_opis
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s,%s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (url) DO UPDATE 
SET
    title = COALESCE(NULLIF(halo_oglasi.title, ''), NULLIF(EXCLUDED.title, '')),
    price_total = COALESCE(halo_oglasi.price_total, EXCLUDED.price_total),
    price_per_m2 = COALESCE(halo_oglasi.price_per_m2, EXCLUDED.price_per_m2),
    tip_nekretnine = COALESCE(NULLIF(halo_oglasi.tip_nekretnine, ''), NULLIF(EXCLUDED.tip_nekretnine, '')),
    kvadratura = COALESCE(halo_oglasi.kvadratura, EXCLUDED.kvadratura),
    broj_soba = COALESCE(halo_oglasi.broj_soba, EXCLUDED.broj_soba),
    oglasivac = COALESCE(NULLIF(halo_oglasi.oglasivac, ''), NULLIF(EXCLUDED.oglasivac, '')),
    tip_objekta = COALESCE(NULLIF(halo_oglasi.tip_objekta, ''), NULLIF(EXCLUDED.tip_objekta, '')),
    stanje_objekta = COALESCE(NULLIF(halo_oglasi.stanje_objekta, ''), NULLIF(EXCLUDED.stanje_objekta, '')),
    grejanje = COALESCE(NULLIF(halo_oglasi.grejanje, ''), NULLIF(EXCLUDED.grejanje, '')),
    sprat = COALESCE(NULLIF(halo_oglasi.sprat, ''), NULLIF(EXCLUDED.sprat, '')),
    ukupna_spratnost = COALESCE(halo_oglasi.ukupna_spratnost, EXCLUDED.ukupna_spratnost),
    uknjizen = COALESCE(halo_oglasi.uknjizen, EXCLUDED.uknjizen),
    terasa = COALESCE(halo_oglasi.terasa, EXCLUDED.terasa),
    interfon = COALESCE(halo_oglasi.interfon, EXCLUDED.interfon),
    klima = COALESCE(halo_oglasi.klima, EXCLUDED.klima),
    video_nadzor = COALESCE(halo_oglasi.video_nadzor, EXCLUDED.video_nadzor),
    internet = COALESCE(halo_oglasi.internet, EXCLUDED.internet),
    parking = COALESCE(halo_oglasi.parking, EXCLUDED.parking),
    garaza = COALESCE(halo_oglasi.garaza, EXCLUDED.garaza),
    lift = COALESCE(halo_oglasi.lift, EXCLUDED.lift),
    podrum = COALESCE(halo_oglasi.podrum, EXCLUDED.podrum),
    linije_gradskog_prevoza = COALESCE(NULLIF(halo_oglasi.linije_gradskog_prevoza, ''), NULLIF(EXCLUDED.linije_gradskog_prevoza, '')),
    datum_objave = COALESCE(halo_oglasi.datum_objave, EXCLUDED.datum_objave),
    dodatni_opis = COALESCE(NULLIF(halo_oglasi.dodatni_opis, ''), NULLIF(EXCLUDED.dodatni_opis, ''))
    """

        values = (
            item.get("url"),
            item.get("title"),
            item.get("price_total"),
            item.get("price_per_m2"),
            item.get("Tip nekretnine"),
            item.get("Kvadratura"),
            item.get("Broj soba"),
            item.get("Oglašivač"),
            item.get("Tip objekta"),
            item.get("Stanje objekta"),
            item.get("Grejanje"),
            item.get("Sprat"),
            item.get("Ukupna spratnost"),
            item.get("Uknjižen"),
            item.get("Terasa"),
            item.get("Interfon"),
            item.get("Klima"),
            item.get("Video nadzor"),
            item.get("Internet"),
            item.get("Parking"),
            item.get("Garaža"),
            item.get("Lift"),
            item.get("Podrum"),
            item.get("Linije gradskog prevoza"),
            item.get("Datum_objave"),
            item.get("Dodatni opis"),
        )

        cursor.execute(query, values)

def insert_row_4zida(cursor,item):
    
        query = """
            INSERT INTO public.z4ida (
                url,
                title,
                price_total,
                price_per_m2,
                tip_nekretnine,
                kvadratura,
                broj_soba,
                oglasivac,
                tip_objekta,
                stanje_objekta,
                grejanje,
                sprat,
                ukupna_spratnost,
                uknjizen,
                terasa,
                interfon,
                klima,
                video_nadzor,
                internet,
                parking,
                garaza,
                lift,
                podrum,
                linije_gradskog_prevoza,
                datum_objave,
                dodatni_opis
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s,%s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (url) DO UPDATE
SET
    title = COALESCE(NULLIF(z4ida.title, ''), NULLIF(EXCLUDED.title, '')),
    price_total = COALESCE(z4ida.price_total, EXCLUDED.price_total),
    price_per_m2 = COALESCE(z4ida.price_per_m2, EXCLUDED.price_per_m2),
    tip_nekretnine = COALESCE(NULLIF(z4ida.tip_nekretnine, ''), NULLIF(EXCLUDED.tip_nekretnine, '')),
    kvadratura = COALESCE(z4ida.kvadratura, EXCLUDED.kvadratura),
    broj_soba = COALESCE(z4ida.broj_soba, EXCLUDED.broj_soba),
    oglasivac = COALESCE(NULLIF(z4ida.oglasivac, ''), NULLIF(EXCLUDED.oglasivac, '')),
    tip_objekta = COALESCE(NULLIF(z4ida.tip_objekta, ''), NULLIF(EXCLUDED.tip_objekta, '')),
    stanje_objekta = COALESCE(NULLIF(z4ida.stanje_objekta, ''), NULLIF(EXCLUDED.stanje_objekta, '')),
    grejanje = COALESCE(NULLIF(z4ida.grejanje, ''), NULLIF(EXCLUDED.grejanje, '')),
    sprat = COALESCE(NULLIF(z4ida.sprat, ''), NULLIF(EXCLUDED.sprat, '')),
    ukupna_spratnost = COALESCE(z4ida.ukupna_spratnost, EXCLUDED.ukupna_spratnost),
    uknjizen = COALESCE(z4ida.uknjizen, EXCLUDED.uknjizen),
    terasa = COALESCE(z4ida.terasa, EXCLUDED.terasa),
    interfon = COALESCE(z4ida.interfon, EXCLUDED.interfon),
    klima = COALESCE(z4ida.klima, EXCLUDED.klima),
    video_nadzor = COALESCE(z4ida.video_nadzor, EXCLUDED.video_nadzor),
    internet = COALESCE(z4ida.internet, EXCLUDED.internet),
    parking = COALESCE(z4ida.parking, EXCLUDED.parking),
    garaza = COALESCE(z4ida.garaza, EXCLUDED.garaza),
    lift = COALESCE(z4ida.lift, EXCLUDED.lift),
    podrum = COALESCE(z4ida.podrum, EXCLUDED.podrum),
    linije_gradskog_prevoza = COALESCE(NULLIF(z4ida.linije_gradskog_prevoza, ''), NULLIF(EXCLUDED.linije_gradskog_prevoza, '')),
    datum_objave = COALESCE(z4ida.datum_objave, EXCLUDED.datum_objave),
    dodatni_opis = COALESCE(NULLIF(z4ida.dodatni_opis, ''), NULLIF(EXCLUDED.dodatni_opis, ''))
        """

        values = (
            item.get("url"),
            item.get("title"),
            item.get("price_total"),
            item.get("price_per_m2"),
            item.get("Tip nekretnine"),
            item.get("Kvadratura"),
            item.get("Broj soba"),
            item.get("Oglašivač"),
            item.get("Tip objekta"),
            item.get("Stanje objekta"),
            item.get("Grejanje"),
            item.get("Sprat"),
            item.get("Ukupna spratnost"),
            item.get("Uknjižen"),
            item.get("Terasa"),
            item.get("Interfon"),
            item.get("Klima"),
            item.get("Video nadzor"),
            item.get("Internet"),
            item.get("Parking"),
            item.get("Garaža"),
            item.get("Lift"),
            item.get("Podrum"),
            item.get("Linije gradskog prevoza"),
            item.get("Datum_objave"),
            item.get("Dodatni opis"),
        )

        cursor.execute(query, values)

def insert_row_nekretnine(cursor,item):

        query = """
            INSERT INTO public.nekretnine_rs (
                url,
                title,
                price_total,
                price_per_m2,
                tip_nekretnine,
                kvadratura,
                broj_soba,
                oglasivac,
                tip_objekta,
                stanje_objekta,
                grejanje,
                sprat,
                ukupna_spratnost,
                uknjizen,
                terasa,
                interfon,
                klima,
                video_nadzor,
                internet,
                parking,
                garaza,
                lift,
                podrum,
                linije_gradskog_prevoza,
                datum_objave,
                dodatni_opis
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s,%s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (url) DO UPDATE
SET
    title = COALESCE(NULLIF(nekretnine_rs.title, ''), NULLIF(EXCLUDED.title, '')),
    price_total = COALESCE(nekretnine_rs.price_total, EXCLUDED.price_total),
    price_per_m2 = COALESCE(nekretnine_rs.price_per_m2, EXCLUDED.price_per_m2),
    tip_nekretnine = COALESCE(NULLIF(nekretnine_rs.tip_nekretnine, ''), NULLIF(EXCLUDED.tip_nekretnine, '')),
    kvadratura = COALESCE(nekretnine_rs.kvadratura, EXCLUDED.kvadratura),
    broj_soba = COALESCE(nekretnine_rs.broj_soba, EXCLUDED.broj_soba),
    oglasivac = COALESCE(NULLIF(nekretnine_rs.oglasivac, ''), NULLIF(EXCLUDED.oglasivac, '')),
    tip_objekta = COALESCE(NULLIF(nekretnine_rs.tip_objekta, ''), NULLIF(EXCLUDED.tip_objekta, '')),
    stanje_objekta = COALESCE(NULLIF(nekretnine_rs.stanje_objekta, ''), NULLIF(EXCLUDED.stanje_objekta, '')),
    grejanje = COALESCE(NULLIF(nekretnine_rs.grejanje, ''), NULLIF(EXCLUDED.grejanje, '')),
    sprat = COALESCE(NULLIF(nekretnine_rs.sprat, ''), NULLIF(EXCLUDED.sprat, '')),
    ukupna_spratnost = COALESCE(nekretnine_rs.ukupna_spratnost, EXCLUDED.ukupna_spratnost),
    uknjizen = COALESCE(nekretnine_rs.uknjizen, EXCLUDED.uknjizen),
    terasa = COALESCE(nekretnine_rs.terasa, EXCLUDED.terasa),
    interfon = COALESCE(nekretnine_rs.interfon, EXCLUDED.interfon),
    klima = COALESCE(nekretnine_rs.klima, EXCLUDED.klima),
    video_nadzor = COALESCE(nekretnine_rs.video_nadzor, EXCLUDED.video_nadzor),
    internet = COALESCE(nekretnine_rs.internet, EXCLUDED.internet),
    parking = COALESCE(nekretnine_rs.parking, EXCLUDED.parking),
    garaza = COALESCE(nekretnine_rs.garaza, EXCLUDED.garaza),
    lift = COALESCE(nekretnine_rs.lift, EXCLUDED.lift),
    podrum = COALESCE(nekretnine_rs.podrum, EXCLUDED.podrum),
    linije_gradskog_prevoza = COALESCE(NULLIF(nekretnine_rs.linije_gradskog_prevoza, ''), NULLIF(EXCLUDED.linije_gradskog_prevoza, '')),
    datum_objave = COALESCE(nekretnine_rs.datum_objave, EXCLUDED.datum_objave),
    dodatni_opis = COALESCE(NULLIF(nekretnine_rs.dodatni_opis, ''), NULLIF(EXCLUDED.dodatni_opis, ''))
    """

        values = (
            item.get("url"),
            item.get("title"),
            item.get("price_total"),
            item.get("price_per_m2"),
            item.get("Tip nekretnine"),
            item.get("Kvadratura"),
            item.get("Broj soba"),
            item.get("Oglašivač"),
            item.get("Tip objekta"),
            item.get("Stanje objekta"),
            item.get("Grejanje"),
            item.get("Sprat"),
            item.get("Ukupna spratnost"),
            item.get("Uknjižen"),
            item.get("Terasa"),
            item.get("Interfon"),
            item.get("Klima"),
            item.get("Video nadzor"),
            item.get("Internet"),
            item.get("Parking"),
            item.get("Garaža"),
            item.get("Lift"),
            item.get("Podrum"),
            item.get("Linije gradskog prevoza"),
            item.get("Datum_objave"),
            item.get("Dodatni opis"),
        )

        cursor.execute(query, values)