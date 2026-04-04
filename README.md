# Serbia Housing

Projekat za prikupljanje, čišćenje i skladištenje podataka o nekretninama sa srpskih sajtova za oglase, sa ciljem da kasnije posluži kao osnova za analizu tržišta i trening modela za predikciju cena nekretnina u Srbiji.

## Trenutno stanje projekta

Projekat je trenutno organizovan u nekoliko glavnih celina:

- `scraper/` – scraperi za pojedinačne sajtove
- `preprocesing/` – pipeline za čišćenje i standardizaciju podataka
- `database/` – konekcija sa PostgreSQL bazom, kreiranje baze/tabela i upis podataka
- `README.md` – dokumentacija projekta

## Šta je do sada urađeno

### 1. Napravljena je struktura projekta
Kod je podeljen logički po odgovornostima:
- scraping
- preprocessing
- database sloj

To je dobar korak jer olakšava dalje širenje projekta na više sajtova i kasnije održavanje.

### 2. Napravljeni su scraperi za više sajtova
Trenutno postoje scraperi za:
- Halo oglasi
- 4zida
- Nekretnine.rs

Svaki scraper prikuplja podatke sa listing i detaljnih stranica oglasa.

### 3. Definisan je skup kolona koje se prate
Za oglase se izvlače bitne informacije kao što su:
- URL oglasa
- naslov
- ukupna cena
- cena po kvadratu
- tip nekretnine
- kvadratura
- broj soba
- oglašivač
- tip i stanje objekta
- grejanje
- sprat i ukupna spratnost
- uknjiženost
- dodatne karakteristike stana
- dodatni opis

### 4. Uveden je preprocessing pipeline
Podaci se pre upisa sređuju kroz poseban pipeline, što je mnogo bolje nego da se sirovi podaci odmah smeštaju u bazu.

To uključuje:
- čišćenje vrednosti
- standardizaciju naziva
- konverziju tipova podataka
- obradu boolean polja
- parsiranje podataka iz dodatnog opisa

### 5. Povezan je PostgreSQL
Napravljen je database sloj koji omogućava:
- povezivanje na bazu
- kreiranje baze
- kreiranje tabela
- upis pojedinačnih redova u odgovarajuću tabelu

### 6. Rešeni su problemi sa tipovima podataka
Tokom upisa u bazu ispravljeni su problemi kao što su:
- boolean kolone koje su dobijale `1/0` umesto `True/False`
- boolean vrednosti koje su ostajale kao string `"da"` / `"ne"`
- neusaglašenost između preprocessinga i SQL šeme

### 7. Dodat je `UNIQUE` constraint na URL
Kolona `url` je postavljena kao jedinstvena, što omogućava:

```sql
ON CONFLICT (url) DO NOTHING
