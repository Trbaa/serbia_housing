import psycopg2
from psycopg2 import sql
from db_config import get_default_connection_params

new_db_name = "scraping_database"


def create_database(db_name, params):
    conn = None

    try:
        conn = psycopg2.connect(**params)
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (db_name,))
        exists = cursor.fetchone()

        if exists:
            print(f"Database '{db_name}' already exists.")
        else:
            query = sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name))
            cursor.execute(query)
            print(f"Database '{db_name}' created successfully.")

        cursor.close()

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        if conn:
            conn.close()


create_database(new_db_name, get_default_connection_params())