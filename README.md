# Serbia Housing — Real Estate Data Pipeline

**Poslednja izmena:** 28. april 2026.

Projekat za automatsko prikupljanje, čišćenje i skladištenje podataka o nekretninama sa srpskih oglasnih sajtova. Izgrađena je pouzdana baza podataka koja se svakodnevno ažurira i može da se koristi za analizu tržišta, vizuelizaciju trendova i razvoj modela za procenu cena nekretnina u Srbiji.

---

## Arhitektura sistema

```
EventBridge (08:00 svaki dan)
        ↓
Lambda funkcija (start-ec2-scraper)
        ↓
EC2 t3.micro (serbia-housing-scraper)
        ↓
Systemd service → python -m main --mode daily
        ↓
┌─────────────┬─────────────┬──────────────┐
│ halo_oglasi │    z4ida    │ nekretnine_rs│
└─────────────┴─────────────┴──────────────┘
        ↓
Raw upis (sirovi podaci) → raw shema
        ↓
Preprocessing pipeline
        ↓
Silver upis (očišćeni podaci) → silver shema
        ↓
dbt run → transformacije i testovi
        ↓
Gold sloj → gold.unified_oglasi
        ↓
Deduplication pipeline
        ↓
gold.unified_deduplicated
        ↓
RDS PostgreSQL (serbia-housing-db)
        ↓
EC2 shutdown (automatski)
```

---

## Arhitektura baze podataka (Medallion Architecture)

Baza je organizovana po **Medallion Architecture** principu — industry standard u Data Engineeringu. Jedna PostgreSQL baza (`scraping_database`) sadrži tri sheme:

### `raw` shema — Bronze sloj
Čuva sirove podatke tačno onako kako su stigli sa sajtova, bez ikakve transformacije. Sve kolone su `text` tip. Služi kao backup — u slučaju greške u preprocessingu uvek se može ponoviti čišćenje od sirovog.

### `silver` shema — Silver sloj
Čuva očišćene i transformisane podatke. Ovo je glavni analitički sloj koji se koristi za upite, analitiku i ML.

### `gold` shema — Gold sloj
Sadrži dve tabele:
- `unified_oglasi` — spaja sva 3 izvora (24,120 oglasa)
- `unified_deduplicated` — deduplikovani oglasi (22,039 oglasa, 2,081 duplikata uklonjeno)

---

## Komponente projekta

### Scraperi (`scraper/`)

Svaki scraper je zadužen za jedan izvor podataka:

- `halo_oglasi.py` — scraper za halooglasi.com
- `z4ida.py` — scraper za 4zida.rs
- `nekretnine_rs.py` — scraper za nekretnine.rs

Svi scraperi koriste **Playwright** za browser automation i **playwright-stealth** za zaobilaženje anti-bot zaštite. Svaki scraper podržava dva moda pokretanja:

- `mode="daily"` — skuplja samo nove oglase, staje čim pronađe 3 uzastopna duplikata (early stop)
- `mode="full"` — prolazi kroz sve stranice, koristi se samo za inicijalno punjenje baze

#### Tok upisa podataka

Za svaki oglas se radi dupli upis:

1. Sirovi dict → `raw.{tabela}` (pre preprocessinga)
2. Očišćen dict → `silver.{tabela}` (nakon preprocessinga)

#### Sortiranje i early stop logika

Svi sajtovi sortiraju oglase od najnovijih:
- halooglasi.com — automatski sortira od najnovijih
- 4zida.rs — `?sortiranje=najnoviji`
- nekretnine.rs — `?order=2`

U `daily` modu, scraper prolazi oglase od najnovijeg ka starijem. Čim nađe 3 uzastopna oglasa koji već postoje u bazi (`oglas_id_exists`) — staje. Ovo garantuje da se ne preskoče novi oglasi u slučaju da sortiranje nije savršeno.

#### Anti-bot zaštita

Svaki scraper koristi:
- `playwright-stealth` — maskira Playwright kao pravi browser
- `human_delay` — random pauze između requestova (800-8000ms)
- `block_resources` — blokira slike, fontove i tracking skripte
- `slow_mo=150` — usporava Playwright akcije
- Rotacija user agenata iz `scraper/user_agents.py`

### Preprocessing (`preprocesing/`)

`pipeline.py` prima sirovi dict od scrapers i vraća očišćen dict spreman za upis u silver shemu. Pipeline čisti svako polje:

- `clean_title` — uklanja cifre, specijalne karaktere
- `clean_price_total` / `clean_price_per_m2` — parsira cene, uklanja valute, rukuje rasponima (npr. `78 000 - 370 500 EUR` → prosek)
- `clean_kvadratura` / `clean_br_soba` — parsira numeričke vrednosti
- `clean_sprat` — konvertuje rimske brojeve, prizemlje, suteren u numeričke vrednosti
- `clean_datum_objave` — parsira datum u Python `date` objekat
- `clean_lokacija` — ekstraktuje lokaciju iz naslova ili opisa oglasa
- `clean_uknjizen`, `clean_terasa`, `clean_lift`... — konvertuje u boolean iz teksta i opisa

### Baza podataka (`database/`)

#### Silver tabele

Sve tri tabele (`silver.halo_oglasi`, `silver.z4ida`, `silver.nekretnine_rs`) imaju identičnu strukturu:

| Kolona | Tip | Opis |
|--------|-----|------|
| `id` | integer | Auto-increment PK |
| `url` | text | URL oglasa |
| `oglas_id` | text UNIQUE | Jedinstveni ID izvučen iz URL-a |
| `title` | text | Naslov oglasa |
| `price_total` | numeric | Ukupna cena u EUR |
| `price_per_m2` | numeric | Cena po m² |
| `tip_nekretnine` | text | stan / kuća |
| `kvadratura` | numeric | Površina u m² |
| `broj_soba` | numeric | Broj soba |
| `oglasivac` | text | agencija / vlasnik |
| `tip_objekta` | text | Novo_gradnja / Stara_gradnja |
| `stanje_objekta` | text | Novo, Lux, Renovirano... |
| `grejanje` | text | centralno, etazno_gas... |
| `sprat` | numeric(5,1) | Sprat (-0.5=suteren, 0=prizemlje, 0.5=vp) |
| `ukupna_spratnost` | integer | Ukupan broj spratova |
| `uknjizen` | boolean | Da li je uknjižen |
| `terasa` | boolean | Da li ima terasu |
| `interfon` | boolean | Da li ima interfon |
| `klima` | boolean | Da li ima klimu |
| `video_nadzor` | boolean | Da li ima video nadzor |
| `internet` | boolean | Da li ima internet |
| `parking` | boolean | Da li ima parking |
| `garaza` | boolean | Da li ima garažu |
| `lift` | boolean | Da li ima lift |
| `podrum` | boolean | Da li ima podrum |
| `linije_gradskog_prevoza` | text | Linije javnog prevoza |
| `datum_objave` | date | Datum objave oglasa |
| `dodatni_opis` | text | Očišćen opis oglasa |
| `lokacija` | text | Ekstraktovana lokacija u Beogradu |
| `created_at` | timestamp | Vreme upisa u bazu |

#### Raw tabele

Sve tri tabele (`raw.halo_oglasi`, `raw.z4ida`, `raw.nekretnine_rs`) imaju identičnu strukturu kao silver, ali su **sve kolone `text` tipa** jer čuvaju sirove podatke bez konverzije.

### dbt transformacije (`dbt_serbia_housing/`)

Nakon što scraperi završe, `main.py` automatski pokreće dbt koji transformiše silver podatke u gold sloj.

**Staging modeli** (`models/staging/`) — tanki wrapper oko silver tabela:
- `stg_halo_oglasi` — standardizuje halooglasi.com podatke, dodaje `izvor` kolonu
- `stg_z4ida` — standardizuje 4zida.rs podatke
- `stg_nekretnine_rs` — standardizuje nekretnine.rs podatke

**Mart modeli** (`models/marts/`) — biznis logika:
- `gold.unified_oglasi` — spaja sva 3 izvora u jednu tabelu (24,120 oglasa)

**Testovi** — dbt automatski proverava kvalitet podataka pri svakom pokretanju:
- `unique` na `oglas_id` — nema duplikata
- `not_null` na `oglas_id` — svaki oglas ima ID
- `accepted_values` na `izvor` — samo poznati izvori

**Pokretanje:**
```bash
cd dbt_serbia_housing
dbt run    # kreira/ažurira modele
dbt test   # proverava kvalitet podataka
dbt docs serve --port 8080  # vizuelna dokumentacija
```

#### Insert logika (`insert_row.py`)

Koristi se `ON CONFLICT (oglas_id) DO UPDATE` — ako oglas već postoji, ažurira samo NULL vrednosti. `COALESCE` logika štiti postojeće podatke od prepisivanja.

Svaki oglas se upisuje dva puta:
- `insert_raw_row_*` — sirovi podaci u `raw` shemu
- `insert_row_*` — očišćeni podaci u `silver` shemu

#### Provera duplikata (`url_checker.py`)

`oglas_id_exists(cursor, oglas_id, table)` — provera da li oglas već postoji u `silver` shemi. Koristi se za early stop u daily modu.

#### `oglas_id` ekstrakcija (`url_checker.py`)

Svaki sajt ima drugačiji format ID-a u URL-u:
- halooglasi.com — numerički, 10+ cifara: `5425647022667`
- 4zida.rs — hex string, 24 karaktera: `69dfc44bf8af725eaf03ca39`
- nekretnine.rs — alphanumerički, 4-20 karaktera: `NksEAVNuU57`

### Deduplication pipeline (`deduplication/`)

Nakon dbt transformacija, `main.py` pokreće pipeline koji detektuje iste stanove oglašene na više sajtova i grupiše ih pod jedinstvenim `stan_id`.

**Rezultati:**

| Metrika | Vrednost |
|---------|---------|
| Ukupno oglasa (`unified_oglasi`) | 24,120 |
| Nakon deduplikacije (`unified_deduplicated`) | 22,039 |
| Uklonjenih duplikata | 2,081 |

**Algoritam:**

1. Učitava `gold.unified_oglasi`, filtrira outliere (cena 20k–2M EUR, kvadratura 15–400 m²)
2. Normalizuje numeričke feature-e: kvadratura, broj_soba, sprat, price_per_m2 (MinMaxScaler)
3. TF-IDF vektorizacija teksta iz `dodatni_opis` (bigrams, min_df=2, max_df=0.95)
4. **Blokiranje** — poredi samo oglase unutar iste lokacije i sličnih kvadratura (early break >5 m²)
5. **Score funkcija** — weighted kombinacija:
   - kvadratura: 25%
   - price_per_m2: 25%
   - tekst (cosine similarity): 25%
   - broj_soba: 15%
   - sprat: 5%
   - lokacija: 5%
   - Boost: ako `tekst > 0.95` → score = 1.0 (identični opisi = isti oglas)
6. **Greedy Clique clustering** — oglas ulazi u klaster samo ako je sličan svim postojećim članovima (prag: 0.92)
7. Filteri kvaliteta: max 10 oglasa po klasteru, max CV cene 10%
8. Upisuje u `gold.unified_deduplicated` sa `stan_id` i `price_avg`

**Pokretanje:**
```bash
python deduplication/dedup_pipeline.py
```

### Konfiguracija baze (`database/db_config.py`)

Čita konekcione parametre iz `.env.aws` fajla:

```
DB_HOST=...
DB_PORT=5433
DB_NAME=scraping_database
DB_USER=postgres
DB_PASSWORD=...
```

### Eksplorativna analiza podataka (`eda/`)

Jupyter notebook sa analizom 23,000+ oglasa iz `gold.unified_oglasi` tabele.

**Analize koje su urađene:**
- Kvalitet podataka — procenat NULL vrednosti po koloni
- Distribucija cena i kvadrature — medijana cene 224,000 EUR, medijana kvadrature 68 m²
- Analiza po lokaciji — Dedinje, Kalemegdan i Knez Mihajlova su najskuplje lokacije
- Trend cena po mesecu (mart 2025 — april 2026)
- Distribucija broja soba — dvosobni i trosobni stanovi dominiraju tržištem
- Korelacija između karakteristika
- Uticaj amenitija na cenu (lift, terasa, parking, garaža, klima, interfon)
- Analiza oglašivača — agencija vs vlasnik

**Pokretanje:**
```bash
cd eda
jupyter notebook
```

---

## AWS infrastruktura

### EC2 — serbia-housing-scraper
- Instance type: `t3.micro` (2 vCPU, 1GB RAM)
- OS: Amazon Linux 2023
- Swap: 2GB (zaštita od OOM crash-a)
- Region: us-east-1

### RDS — serbia-housing-db
- Engine: PostgreSQL 16
- Instance: `db.t3.micro`
- Storage: 20GB gp2
- Port: 5433
- Public access: Yes (zaštićeno security grupom)

### Lambda — start-ec2-scraper
Startuje EC2 instancu:
```python
import boto3
def lambda_handler(event, context):
    ec2 = boto3.client('ec2', region_name='us-east-1')
    ec2.start_instances(InstanceIds=['INSTANCE_ID'])
```

### EventBridge Scheduler
Pokreće Lambda svaki dan u 08:00 po beogradskom vremenu (`Europe/Belgrade` timezone).

### Systemd service (`/etc/systemd/system/scraper.service`)
Automatski pokreće scraper čim se EC2 startuje:
```ini
[Unit]
Description=Daily scraper
After=network.target

[Service]
Type=oneshot
User=ec2-user
WorkingDirectory=/home/ec2-user/serbia_housing
ExecStart=/home/ec2-user/scraper_env/bin/python -m main --mode daily
StandardOutput=append:/home/ec2-user/scraper.log
StandardError=append:/home/ec2-user/scraper.log

[Install]
WantedBy=multi-user.target
```

---

## Pokretanje

### Daily update (automatski svaki dan)
```bash
python -m main --mode daily
```
Skuplja samo nove oglase. Brzo završava — obično par minuta.

### Full scrape (inicijalno punjenje baze)
```bash
python -m main --mode full
```
Prolazi kroz sve stranice. Traje nekoliko sati.

### Pojedinačni scraper
```bash
python -c "from scraper.halo_oglasi import run_halo_oglasi; run_halo_oglasi(max_pages=2, mode='daily')"
```

---

## Praćenje

### Log na EC2
```bash
tail -f /home/ec2-user/scraper.log
```

### Broj oglasa u bazi
```sql
SELECT
    (SELECT COUNT(*) FROM silver.halo_oglasi)   AS halo,
    (SELECT COUNT(*) FROM silver.z4ida)         AS z4ida,
    (SELECT COUNT(*) FROM silver.nekretnine_rs) AS nekretnine;
```

### Unified vs deduplicated
```sql
SELECT
    (SELECT COUNT(*) FROM gold.unified_oglasi)       AS unified,
    (SELECT COUNT(*) FROM gold.unified_deduplicated) AS deduplicated,
    (SELECT COUNT(*) FROM gold.unified_oglasi) -
    (SELECT COUNT(*) FROM gold.unified_deduplicated) AS uklonjenih_duplikata;
```

### Provera klastera
```sql
SELECT stan_id, COUNT(*) AS n_oglasa, price_avg
FROM gold.unified_deduplicated
GROUP BY stan_id, price_avg
HAVING COUNT(*) > 1
ORDER BY n_oglasa DESC
LIMIT 10;
```

### Provera raw vs silver
```sql
SELECT
    (SELECT COUNT(*) FROM raw.halo_oglasi)      AS raw_halo,
    (SELECT COUNT(*) FROM silver.halo_oglasi)   AS silver_halo,
    (SELECT COUNT(*) FROM raw.z4ida)            AS raw_z4ida,
    (SELECT COUNT(*) FROM silver.z4ida)         AS silver_z4ida,
    (SELECT COUNT(*) FROM raw.nekretnine_rs)    AS raw_nekretnine,
    (SELECT COUNT(*) FROM silver.nekretnine_rs) AS silver_nekretnine;
```

---

## Trenutno stanje baze

| Izvor | Oglasa |
|-------|--------|
| halooglasi.com | ~8,200 |
| 4zida.rs | ~3,400 |
| nekretnine.rs | ~12,500 |
| **Ukupno (unified_oglasi)** | **24,120** |
| **Nakon deduplikacije** | **22,039** |
| **Uklonjenih duplikata** | **2,081** |

---

## Sledeci koraci

- ~~**dbt**~~ ✅ — transformacije i `unified_oglasi` tabela implementirane
- ~~**Analitika**~~ ✅ — eksplorativna analiza podataka završena
- ~~**Deduplication**~~ ✅ — pipeline implementiran, 2,081 duplikata uklonjeno
- **Feature engineering** — priprema podataka za ML modele
- **Model za procenu cena** — predikcija cena nekretnina na osnovu karakteristika
- **Grafana dashboard** — vizuelizacija podataka
- **Proxy rotacija** — residential proxy za bolju anti-bot zaštitu