import re
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv(".env.aws")

# ── Lista lokacija (sortirana po duzini — duze ime ima prioritet) ──────────
LOKACIJE = sorted([
    # Opštine
    "Stari Grad", "Savski Venac", "Vracar", "Novi Beograd", "Zemun",
    "Palilula", "Vozdovac", "Cukarica", "Rakovica", "Zvezdara",
    "Grocka", "Barajevo", "Mladenovac", "Lazarevac", "Obrenovac",
    "Surcin", "Sopot",

    # Šira gradska naselja
    "Banjica", "Dedinje", "Senjak", "Banovo Brdo", "Cerak",
    "Cerak Vinogradi", "Konjarnik", "Karaburma", "Mirijevo",
    "Mirijevo 1", "Mirijevo 2", "Mirijevo 3",
    "Zeleznik", "Altina", "Borca", "Borca 2", "Borca 3",
    "Krnjaca", "Kotez",
    "Batajnica", "Bezanijska Kosa", "Bezanijska Kosa 1",
    "Bezanijska Kosa 2", "Bezanijska Kosa 3",
    "Blok 1", "Blok 2", "Blok 3", "Blok 4", "Blok 7",
    "Blok 9", "Blok 9a", "Blok 11c", "Blok 12",
    "Blok 19a", "Blok 21", "Blok 22", "Blok 23",
    "Blok 25", "Blok 26", "Blok 28", "Blok 29",
    "Blok 30", "Blok 33", "Blok 37", "Blok 38",
    "Blok 44", "Blok 45", "Blok 61", "Blok 62",
    "Blok 63", "Blok 64", "Blok 67", "Blok 67a",
    "Blok 70", "Blok 70A", "Blok 72", "Blok 73",

    # Mikro lokacije
    "Avala", "Filmski Grad", "Vidikovac", "Petlovo Brdo",
    "Labudovo Brdo", "Kanarevo Brdo", "Miljakovac",
    "Miljakovac 1", "Miljakovac 2", "Miljakovac 3",
    "Resnik", "Kijevo", "Zarkovo", "Julino Brdo",
    "Kosutnjak", "Topcider", "Autokomanda",
    "Slavija", "Kalemegdan", "Dorcol",
    "Donji Dorcol", "Gornji Dorcol",
    "Crveni Krst", "Cvetkova Pijaca",
    "Lion", "Djeram", "Hadzipopovac",
    "Bogoslovija", "Gradska Bolnica",
    "Visnjicka Banja", "Visnjica",
    "Rospi Cuprija", "Ada Huja",
    "Ovca", "Padinska Skela",
    "Kovilovo", "Besni Fok", "Dunavac",

    # Zemun / NBG
    "Zemun Polje", "Nova Galenika", "Galenika",
    "Altina 2", "Pregrevica",
    "Gornji Grad", "Donji Grad",
    "Retenzija", "Ledine", "Surcinsko Polje",
    "Plavi Horizonti",

    # Južni deo
    "Jajinci", "Pinosava", "Beli Potok",
    "Ripanj", "Zuce", "Vrcin", "Lestane",
    "Kaludjerica", "Kumodraz",

    # Šira naselja BG (iz tvoje liste)
    "Veliki Mokri Lug", "Mali Mokri Lug",
    "Knezevac", "Stara Rakovica",
    "Sremcica", "Rucka", "Umka",
    "Velika Mostanica", "Mala Mostanica",
    "Ruzanj",

    # Grocka
    "Grocka", "Begaljica", "Bolec",
    "Vinca", "Ritopek", "Zaklopaca",
    "Leštane", "Vrcin",

    # Barajevo
    "Barajevo", "Arandjelovac", "Bacevac",
    "Beljina", "Meljak", "Lisovic",
    "Manic", "Guncati",

    # Lazarevac
    "Lazarevac", "Veliki Crljeni", "Mali Crljeni",
    "Vreoci", "Rudovci", "Zeoke",
    "Junkovac", "Petka", "Dudovica",

    # Mladenovac
    "Mladenovac", "Kovacevac", "Koracica",
    "Velika Ivanca", "Velika Krsna",
    "Jagnjilo", "Dubona", "Markovac",

    # Obrenovac
    "Obrenovac", "Baric", "Zabrezje",
    "Zvecka", "Skela", "Stubline",
    "Urovci", "Grabovac", "Piroman",

    # Palilula šira
    "Veliko Selo", "Slanci",

    # Sopot
    "Sopot", "Ralja", "Rogaca",
    "Nemenikuce", "Popovic", "Slatina",
    "Sibnica", "Parcani",

    # --- BELGRADE WATERFRONT ---
    "Beograd na vodi", "BG na vodi", "Bnv", "Belgrade Waterfront",
    "BW", "BW Residences", "BW Residence",
    "BW Vista", "BW Vista Tower",
    "BW Arcadia", "BW Aurora", "BW Magnolia",
    "BW Parkview", "BW Park View",
    "BW Verde", "BW Scala", "BW Terra",
    "BW Metropolitan", "BW Quartet",
    "BW Riviera", "BW Libera",

    # --- KULA / ST REGIS ---
    "Kula Beograd", "Kula Belgrade Waterfront",
    "Belgrade Tower", "BW Tower",
    "St Regis", "St. Regis", "St Regis Belgrade",
    "St Regis Residences", "St. Regis Residences",
    "StRegis", "St.Regis",

    # --- LUKSUZ ---
    "West 65", "West65", "West 65 Tower",
    "Wellport", "Wellport Kula",
    "A blok", "A Blok", "A-Block",
    "Airport City", "Airport City Belgrade",
    "Green Residence",
    "The One", "The One Novi Beograd",
    "Savada", "Savada 2", "Savada 3",
    "Oaza", "Belvil", "Belville",

    # Premium centar
    "Knez Mihailova", "Obilicev Venac",
    "Studentski trg", "Trg republike",
    "Terazije", "Andricev venac",

    # Ostalo
    "Stepa Stepanovic", "Brace Jerkovic",
    "Medakovic", "Medakovic 1", "Medakovic 2", "Medakovic 3",
    "Dusanovac", "Dusanovac Posta",
    "Učiteljsko Naselje", "Konjarnik 2"
], key=len, reverse=True)


# ── Helper funkcije ────────────────────────────────────────────────────────
def _normalize(tekst: str) -> str:
    """Lowercase + zamena dijakritika da matchujemo i 'Vracar' i 'Vračar'."""
    zamene = {
        'č': 'c', 'ć': 'c', 'š': 's', 'ž': 'z', 'đ': 'd',
        'Č': 'c', 'Ć': 'c', 'Š': 's', 'Ž': 'z', 'Đ': 'd',
    }
    tekst = tekst.lower()
    for orig, repl in zamene.items():
        tekst = tekst.replace(orig, repl)
    return tekst


# Unapred kompajlirani regex pattern za svaku lokaciju — brze od re.compile u loopu
_PATTERNS = [
    (re.compile(r'\b' + re.escape(_normalize(lok))), lok)
    for lok in LOKACIJE
]


def izvuci_lokaciju(title: str | None, opis: str | None) -> str:
    """
    Trazi lokaciju u title prvo, pa u opisu kao fallback.
    Vraca 'Nepoznato' ako ne nadje nista.
    """
    for tekst in [title, opis]:
        if not tekst or str(tekst).strip() in ('', 'nan', 'None'):
            continue
        normalizovan = _normalize(str(tekst))
        for pattern, lokacija in _PATTERNS:
            if pattern.search(normalizovan):
                return lokacija
    return "Nepoznato"


# ── Glavni update ──────────────────────────────────────────────────────────
def update_tabela(conn, tabela: str) -> None:
    print(f"\n{'='*50}")
    print(f"Tabela: {tabela}")

    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT id, title, dodatni_opis
            FROM {tabela}
            WHERE lokacija IS NULL
            ORDER BY id ASC
        """)
        rows = cur.fetchall()

    ukupno = len(rows)
    print(f"Oglasa za update: {ukupno}")

    if ukupno == 0:
        print("Nema oglasa za update.")
        return

    # Izracunaj sve lokacije lokalno u Pythonu
    values = []
    for row_id, title, opis in rows:
        lokacija = izvuci_lokaciju(title, opis)
        values.append((lokacija, row_id))

    nepoznato = sum(1 for lok, _ in values if lok == "Nepoznato")
    nadjena   = ukupno - nepoznato

    # Jedan batch UPDATE umesto 8000+ pojedinacnih
    with conn.cursor() as cur:
        cur.executemany(
            f"UPDATE {tabela} SET lokacija = %s WHERE id = %s",
            values
        )
    conn.commit()

    print(f"Zavrseno: {nadjena} lokacija nadjena | {nepoznato} Nepoznato")
    print(f"Procenat pokrivanja: {round(nadjena/ukupno*100, 1)}%")

def main():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

    try:
        for tabela in ["halo_oglasi", "z4ida", "nekretnine_rs"]:
            update_tabela(conn, tabela)
    finally:
        conn.close()

    print("\nSve tabele azurirane.")


if __name__ == "__main__":
    main()