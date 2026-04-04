import psycopg2
from db_config import get_default_connection_params


def insert_row(item):
    conn = None
    cursor = None

    try:
        conn = psycopg2.connect(**get_default_connection_params())
        cursor = conn.cursor()

        query = """
            INSERT INTO halo_oglasi (
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
                telefon,
                interfon,
                klima,
                video_nadzor,
                topla_voda,
                internet,
                parking,
                garaza,
                lift,
                podrum,
                linije_gradskog_prevoza,
                dodatni_opis
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (url) DO NOTHING
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
            item.get("Telefon"),
            item.get("Interfon"),
            item.get("Klima"),
            item.get("Video nadzor"),
            item.get("Topla voda"),
            item.get("Internet"),
            item.get("Parking"),
            item.get("Garaža"),
            item.get("Lift"),
            item.get("Podrum"),
            item.get("Linije gradskog prevoza"),
            item.get("Dodatni opis"),
        )

        cursor.execute(query, values)
        conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An error occurred: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()