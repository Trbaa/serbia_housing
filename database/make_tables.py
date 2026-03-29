import psycopg2
from db_config import get_scraping_db_connection_params

CREATE_TABLES_QUERIES = [
    """
    CREATE TABLE IF NOT EXISTS halo_oglasi (
        id SERIAL PRIMARY KEY,
        url TEXT,
        title TEXT,
        price_total NUMERIC,
        price_per_m2 NUMERIC,
        tip_nekretnine TEXT,
        kvadratura NUMERIC,
        broj_soba NUMERIC,
        oglasivac TEXT,
        tip_objekta TEXT,
        stanje_objekta TEXT,
        grejanje TEXT,
        sprat TEXT,
        ukupna_spratnost INTEGER,
        uknjizen BOOLEAN,
        terasa BOOLEAN,
        telefon BOOLEAN,
        interfon BOOLEAN,
        klima BOOLEAN,
        video_nadzor BOOLEAN,
        topla_voda BOOLEAN,
        internet BOOLEAN,
        parking BOOLEAN,
        garaza BOOLEAN,
        lift BOOLEAN,
        podrum BOOLEAN,
        linije_gradskog_prevoza TEXT,
        dodatni_opis TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS z4ida (
        id SERIAL PRIMARY KEY,
        url TEXT,
        title TEXT,
        price_total NUMERIC,
        price_per_m2 NUMERIC,
        tip_nekretnine TEXT,
        kvadratura NUMERIC,
        broj_soba NUMERIC,
        oglasivac TEXT,
        tip_objekta TEXT,
        stanje_objekta TEXT,
        grejanje TEXT,
        sprat TEXT,
        ukupna_spratnost INTEGER,
        uknjizen BOOLEAN,
        terasa BOOLEAN,
        telefon BOOLEAN,
        interfon BOOLEAN,
        klima BOOLEAN,
        video_nadzor BOOLEAN,
        topla_voda BOOLEAN,
        internet BOOLEAN,
        parking BOOLEAN,
        garaza BOOLEAN,
        lift BOOLEAN,
        podrum BOOLEAN,
        linije_gradskog_prevoza TEXT,
        dodatni_opis TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS nekretnine_rs (
        id SERIAL PRIMARY KEY,
        url TEXT,
        title TEXT,
        price_total NUMERIC,
        price_per_m2 NUMERIC,
        tip_nekretnine TEXT,
        kvadratura NUMERIC,
        broj_soba NUMERIC,
        oglasivac TEXT,
        tip_objekta TEXT,
        stanje_objekta TEXT,
        grejanje TEXT,
        sprat TEXT,
        ukupna_spratnost INTEGER,
        uknjizen BOOLEAN,
        terasa BOOLEAN,
        telefon BOOLEAN,
        interfon BOOLEAN,
        klima BOOLEAN,
        video_nadzor BOOLEAN,
        topla_voda BOOLEAN,
        internet BOOLEAN,
        parking BOOLEAN,
        garaza BOOLEAN,
        lift BOOLEAN,
        podrum BOOLEAN,
        linije_gradskog_prevoza TEXT,
        dodatni_opis TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
]

def create_tables():
    conn = None

    try:
        conn = psycopg2.connect(**get_scraping_db_connection_params())
        conn.autocommit = True
        cursor = conn.cursor()

        for query in CREATE_TABLES_QUERIES:
            cursor.execute(query)

        print("All tables created successfully.")
        cursor.close()

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        if conn:
            conn.close()

create_tables()