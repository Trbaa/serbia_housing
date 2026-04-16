# Serbia Housing — Real Estate Data Pipeline

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
Preprocessing pipeline
        ↓
RDS PostgreSQL (serbia-housing-db)
        ↓
EC2 shutdown (automatski)
```

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

`pipeline.py` prima sirovi dict od scrapers i vraća očišćen dict spreman za upis u bazu. Pipeline čisti svako polje:

- `clean_title` — uklanja cifre, specijalne karaktere
- `clean_price_total` / `clean_price_per_m2` — parsira cene, uklanja valute
- `clean_kvadratura` / `clean_br_soba` — parsira numeričke vrednosti
- `clean_sprat` — konvertuje rimske brojeve, prizemlje, suteren u numeričke vrednosti
- `clean_datum_objave` — parsira datum u Python `date` objekat
- `clean_uknjizen`, `clean_terasa`, `clean_lift`... — konvertuje u boolean iz teksta i opisa

### Baza podataka (`database/`)

#### Tabele

Sve tri tabele (`halo_oglasi`, `z4ida`, `nekretnine_rs`) imaju identičnu strukturu:

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
| `izvor` | text | halo / 4zida / nekretnine |
| `oglas_id` | text UNIQUE | ID oglasa iz URL-a |
| `created_at` | timestamp | Vreme upisa u bazu |

#### Insert logika (`insert_row.py`)

Koristi se `ON CONFLICT (oglas_id) DO UPDATE` — ako oglas već postoji, ažurira samo NULL vrednosti. `COALESCE` logika štiti postojeće podatke od prepisivanja.

#### Provjera duplikata (`oglas_checker.py`)

`oglas_id_exists(cursor, oglas_id, table)` — jednostavna provjera da li oglas već postoji u bazi. Koristi se za early stop u daily modu.

#### `oglas_id` ekstrakcija (`url_checker.py`)

Svaki sajt ima drugačiji format ID-a u URL-u:
- halooglasi.com — numerički, 10+ cifara: `5425647022667`
- 4zida.rs — hex string, 24 karaktera: `69dfc44bf8af725eaf03ca39`
- nekretnine.rs — alphanumerički, 4-20 karaktera: `NksEAVNuU57`

### Konfiguracija baze (`database/db_config.py`)

Čita konekcione parametre iz `.env` fajla:

```
DB_HOST=...
DB_PORT=5433
DB_NAME=scraping_database
DB_USER=postgres
DB_PASSWORD=...
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
[Service]
Type=oneshot
TimeoutStartSec=0
ExecStart=/home/ec2-user/scraper_env/bin/python -u -m main --mode daily
ExecStartPost=/usr/sbin/shutdown -h now
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
    (SELECT COUNT(*) FROM halo_oglasi)   AS halo,
    (SELECT COUNT(*) FROM z4ida)         AS z4ida,
    (SELECT COUNT(*) FROM nekretnine_rs) AS nekretnine;
```

### Provjera duplikata
```sql
SELECT oglas_id, COUNT(*) AS broj
FROM halo_oglasi
WHERE oglas_id IS NOT NULL
GROUP BY oglas_id
HAVING COUNT(*) > 1;
```

---

## Trenutno stanje baze

| Izvor | Oglasa |
|-------|--------|
| halooglasi.com | ~8,100 |
| 4zida.rs | ~2,500 |
| nekretnine.rs | ~9,300 |
| **Ukupno** | **~19,900** |

---

## Sledeći koraci

- **Analitika** — eksplorativna analiza podataka, vizuelizacija trendova
- **Feature engineering** — priprema podataka za ML modele
- **Model za procenu cena** — predikcija cena nekretnina na osnovu karakteristika
- **Dashboard** — vizuelizacija podataka (Metabase ili custom)
- **Proxy rotacija** — residential proxy za bolju anti-bot zaštitu