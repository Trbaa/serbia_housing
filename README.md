# Serbia Housing — Real Estate Data Pipeline

**Poslednja izmena:** 9. maj 2026.

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
dbt run → transformacije i testovi (incremental merge)
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
- `unified_oglasi` — spaja sva 3 izvora (~27,200 oglasa)
- `unified_deduplicated` — deduplikovani oglasi (~20,700 jedinstvenih stanova)

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

U `daily` modu, scraper prolazi oglase od najnovijeg ka starijem. Čim nađe 3 uzastopna oglasa koji već postoje u bazi (`oglas_id_exists`) — staje.

#### Anti-bot zaštita

Svaki scraper koristi:
- `playwright-stealth` — maskira Playwright kao pravi browser
- `human_delay` — random pauze između requestova (800-8000ms)
- `block_resources` — blokira slike, fontove i tracking skripte
- `slow_mo=150` — usporava Playwright akcije
- Rotacija user agenata iz `scraper/user_agents.py`

### Preprocessing (`preprocesing/`)

`pipeline.py` prima sirovi dict od scrapers i vraća očišćen dict spreman za upis u silver shemu:

- `clean_title` — uklanja cifre, specijalne karaktere
- `clean_price_total` / `clean_price_per_m2` — parsira cene, uklanja valute, rukuje rasponima
- `clean_kvadratura` / `clean_br_soba` — parsira numeričke vrednosti
- `clean_sprat` — konvertuje rimske brojeve, prizemlje, suteren u numeričke vrednosti
- `clean_datum_objave` — parsira datum u Python `date` objekat
- `clean_lokacija` — ekstraktuje lokaciju iz naslova ili opisa oglasa
- `clean_uknjizen`, `clean_terasa`, `clean_lift`... — konvertuje u boolean

### Lokacija update (`database/update_lokacija.py`)

Skripta koja ažurira `lokacija` kolonu u silver tabelama za oglase gde je vrednost `NULL` ili `'Nepoznato'`. Koristi regex matching sa listom od 200+ beogradskih lokacija, normalizovanih za dijakritike.

- Čita oglase gde je `lokacija IS NULL OR lokacija = 'Nepoznato'`
- Traži lokaciju u `title` i `dodatni_opis` poljima
- Batch UPDATE koristeći `psycopg2.extras.execute_values` (10-50x brže od executemany)
- Nakon pokretanja, `dbt run` automatski propaguje izmene u gold sloj

**Pokretanje:**
```bash
python database/update_lokacija.py
```

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
| `price_per_m2` | numeric | Cena po m² (može biti korumpirana — koristiti `price_per_m2_calc`) |
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

Identična struktura kao silver, ali su **sve kolone `text` tipa**.

### dbt transformacije (`dbt_serbia_housing/`)

Nakon što scraperi završe, `main.py` automatski pokreće dbt koji transformiše silver podatke u gold sloj.

**Staging modeli** (`models/staging/`) — svi konfigurisani kao `incremental` sa `merge` strategijom:
- `stg_halo_oglasi` — standardizuje halooglasi.com podatke
- `stg_z4ida` — standardizuje 4zida.rs podatke
- `stg_nekretnine_rs` — standardizuje nekretnine.rs podatke

**Mart modeli** (`models/marts/`):
- `gold.unified_oglasi` — spaja sva 3 izvora, `incremental` + `merge` strategija

**Incremental strategija:**
```sql
{{ config(
    materialized='incremental',
    unique_key='unified_id',
    incremental_strategy='merge'
) }}
```
- Novi oglasi → INSERT
- Postojeći oglasi → UPDATE (lokacija, price_avg, stan_id)
- Brže od `DROP + CREATE` svaki run

**Testovi** — 13/13 prolaze pri svakom pokretanju:
- `unique` na `oglas_id` i `unified_id`
- `not_null` na ključnim kolonama
- `accepted_values` na `izvor`

**Pokretanje:**
```bash
cd dbt_serbia_housing
dbt run
dbt test
dbt docs serve --port 8080
```

### Deduplication pipeline (`deduplication/dedup_pipeline.py`)

Nakon dbt transformacija, pipeline detektuje iste stanove oglašene na više sajtova.

**Algoritam:**
1. Učitava `gold.unified_oglasi`, filtrira outliere (cena 20k–2M EUR, kvadratura 15–400 m²)
2. Normalizuje numeričke feature-e (MinMaxScaler)
3. TF-IDF vektorizacija `dodatni_opis` (bigrams, min_df=2, max_df=0.95)
4. Blokiranje — poredi samo oglase unutar iste lokacije i sličnih kvadratura (break >5 m²)
5. Score funkcija — weighted kombinacija (kvadratura 25%, price_per_m2 25%, tekst 25%, broj_soba 15%, sprat 5%, lokacija 5%)
6. Greedy Clique clustering (prag: 0.92)
7. Filteri kvaliteta: max 10 oglasa po klasteru, max CV cene 10%

**Upis u bazu** — `ON CONFLICT DO UPDATE` ažurira lokaciju i cenu za postojeće oglase:
```sql
ON CONFLICT (oglas_id) DO UPDATE SET
    lokacija  = EXCLUDED.lokacija,
    price_avg = EXCLUDED.price_avg,
    stan_id   = EXCLUDED.stan_id
```

**Pokretanje:**
```bash
python deduplication/dedup_pipeline.py
```

---

## Poznati problemi sa podacima

### `price_per_m2` kolona je korumpirana
`price_per_m2` u gold tabelama je kalkulisana pre normalizacije valute (pre konverzije RSD → EUR). Za ML i analitiku uvek koristiti ručno kalkulisanu vrednost:
```python
df["price_per_m2_calc"] = df["price_total"] / df["kvadratura"]
```

### `sprat_ratio > 1` — dirty podaci
18 oglasa sa nekretnine.rs ima `sprat > ukupna_spratnost` zbog greške oglašivača. Za ML pipeline filtrirati:
```python
mask_valid = df["sprat_ratio"].between(0, 1)
df = df[mask_valid].copy()
```

### Boolean kolone čitaju se kao `object`
PostgreSQL `boolean` kolone sa NULL vrednostima pandas učitava kao `object` tip sa vrednostima `True`, `False`, `None`. Konverzija:
```python
bool_cols = ["uknjizen", "terasa", "interfon", "klima", "video_nadzor",
             "internet", "parking", "garaza", "lift", "podrum"]
df[bool_cols] = df[bool_cols].apply(lambda col: col.map({True: True, False: False}))
```

### Lokacija — ~40% oglasa bez lokacije
Po izvoru: 4zida 53.5%, halooglasi 35.9%, nekretnine.rs 39.5% nema lokaciju.
Rešenje: pokrenuti `update_lokacija.py` koji regex-om iz naslova i opisa ekstraktuje lokaciju.

---

## AWS infrastruktura

### EC2 — serbia-housing-scraper
- Instance type: `t3.micro` (2 vCPU, 1GB RAM)
- OS: Amazon Linux 2023
- Swap: 2GB (zaštita od OOM crash-a)
- Region: us-east-1
- IAM role: `ec2-cloudwatch-role` (CloudWatchAgentServerPolicy)

### RDS — serbia-housing-db
- Engine: PostgreSQL 16
- Instance: `db.t3.micro`
- Storage: 20GB gp2
- Port: 5433

### Lambda — start-ec2-scraper
```python
import boto3
def lambda_handler(event, context):
    ec2 = boto3.client('ec2', region_name='us-east-1')
    ec2.start_instances(InstanceIds=['INSTANCE_ID'])
```

### EventBridge Scheduler
Pokreće Lambda svaki dan u 08:00 po beogradskom vremenu (`Europe/Belgrade`).

### CloudWatch Logs
Agent instaliran na EC2, prati `/home/ec2-user/scraper.log`:
- Log group: `serbia-housing-scraper`
- Log stream: `{instance_id}`
- Retention: 30 dana
- Live Tail dostupan u AWS konzoli

### Systemd service
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

## Feature Engineering (u toku)

Polazna tabela: `gold.unified_deduplicated`, vremenski split:
- Train: `datum_objave <= feb 2026`
- Validacija: `mart 2026`
- Test: `>= april 2026`

| Feature | Formula | Status |
|---------|---------|--------|
| `price_per_m2_calc` | `price_total / kvadratura` | ✅ |
| `sprat_ratio` | `sprat / ukupna_spratnost` | ✅ |
| `amenity_score` | broj `True` boolean kolona | ✅ |
| `je_novogradnja`, `je_agencija` | preskočeno — dostupno iz `stanje_objekta` i `oglasivac` | ⏭️ |
| `lokacija_encoded` | target encoding (cross-fold) | ⏳ |
| `starost_oglasa` | dani od `datum_objave` | ⏳ |

---

## ML Model (planirano)

- **Model:** LightGBM (nativno rukuje NULL vrednostima)
- **Ciljna promenljiva:** `price_total`
- **Evaluacija:** RMSE, MAE, R², SHAP vrednosti
- **Deployment:** FastAPI `/predict` endpoint
- **Pipeline:** sklearn `ColumnTransformer` + `Pipeline` (jedan objekat za deployment)

---

## Pokretanje

### Daily update (automatski svaki dan)
```bash
python -m main --mode daily
```

### Full scrape (inicijalno punjenje baze)
```bash
python -m main --mode full
```

### Lokacija update
```bash
python database/update_lokacija.py
```

---

## Praćenje

### Log na EC2
```bash
tail -f /home/ec2-user/scraper.log
```

### CloudWatch Live Tail
AWS konzola → CloudWatch → Live Tail → log group: `serbia-housing-scraper`

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

---

## Trenutno stanje baze

| Izvor | Oglasa |
|-------|--------|
| halooglasi.com | ~8,300 |
| 4zida.rs | ~3,900 |
| nekretnine.rs | ~15,000 |
| **Ukupno (unified_oglasi)** | **~27,200** |
| **Nakon deduplikacije** | **~20,700** |

---

## Sledeći koraci

- ~~**dbt**~~ ✅ — incremental merge transformacije implementirane
- ~~**Analitika**~~ ✅ — eksplorativna analiza podataka završena
- ~~**Deduplication**~~ ✅ — pipeline sa ON CONFLICT DO UPDATE implementiran
- ~~**CloudWatch**~~ ✅ — logovanje na AWS podešeno
- ~~**Lokacija update**~~ ✅ — batch update skripta implementirana
- **Feature engineering** ⏳ — u toku (price_per_m2_calc, sprat_ratio, amenity_score gotovi)
- **ML model** ⏳ — LightGBM hedonic pricing model
- **FastAPI deployment** ⏳ — `/predict` endpoint
- **Grafana dashboard** — vizuelizacija podataka
- **Proxy rotacija** — residential proxy za bolju anti-bot zaštitu