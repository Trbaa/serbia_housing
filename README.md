# Serbia Housing Scraper

Projekat za prikupljanje podataka o nekretninama sa više sajtova za oglašavanje u Srbiji, njihovo skladištenje u PostgreSQL bazu i kasniju obradu za analizu tržišta i ML modele za predikciju cena stanova.

## Cilj projekta

Cilj projekta je da se izgradi stabilan data pipeline koji:

- skrejpuje oglase sa više sajtova za nekretnine
- čuva podatke u PostgreSQL bazu umesto u CSV fajlove
- omogućava dalje čišćenje, analizu i poređenje oglasa
- priprema kvalitetan dataset za budući machine learning model za predikciju cena stanova u Srbiji

## Trenutno urađeno

Do sada je završeno:

- napravljena PostgreSQL baza `scraping_database`
- napravljene 3 odvojene tabele unutar iste baze:
  - `halo_oglasi`
  - `z4ida`
  - `nekretnine_rs`
- uvedena konfiguracija preko `.env` fajla
- uklonjena potreba za hardkodovanjem user/password podataka u kodu
- dodata zaštita da se osetljivi podaci ne guraju na GitHub
- definisana zajednička struktura kolona za sve scrape izvore
- postavljen temelj za prelazak sa CSV logike na direktan upis u bazu

## Struktura projekta

Primer trenutne strukture projekta:

```bash
Serbia_housing/
│
├── .env
├── .gitignore
├── README.md
├── scraper_env/
│
├── database/
│   ├── db_config.py
│   ├── make_database.py
│   └── make_tables.py
│
├── scrapers/
│   ├── halo_oglasi_scraper.py
│   ├── z4ida_scraper.py
│   └── nekretnine_rs_scraper.py
│
└── data/