# Serbia Housing

Projekat za prikupljanje, čišćenje i skladištenje podataka o nekretninama sa srpskih sajtova za oglase. Cilj projekta je izgradnja pouzdane baze podataka koja kasnije može da se koristi za analizu tržišta, vizuelizaciju trendova i razvoj modela za procenu cena nekretnina u Srbiji.

Ovaj README je osvežena verzija postojeće dokumentacije i uključuje novi korak u arhitekturi projekta: paralelno pokretanje sva 3 scrapera iz jednog `main` fajla, preprocessing podataka i individualni upis u odgovarajuće tabele unutar zajedničke PostgreSQL baze.

## Trenutno stanje projekta

Projekat je trenutno funkcionalan end-to-end za tri izvora podataka:

- **Halo oglasi**
- **4zida**
- **Nekretnine.rs**

Za svaki izvor postoji poseban scraper, a svi scraperi se sada mogu pokretati paralelno iz jednog centralnog ulaznog fajla. Nakon scrape-a, podaci prolaze kroz preprocessing pipeline i zatim se pojedinačno upisuju u odgovarajuću tabelu u okviru zajedničke baze.

Sistem je testiran i potvrđeno je da radi:

- za svaki scraper pojedinačno
- za paralelno pokretanje sva 3 scrapera
- za preprocessing pipeline
- za individualni insert u bazu
- za upis u svaku ciljnu tabelu unutar zajedničke PostgreSQL baze

## Arhitektura projekta

Projekat je organizovan u nekoliko glavnih celina:

- `scraper/` – scraperi za pojedinačne sajtove
- `preprocesing/` – pipeline za čišćenje i standardizaciju podataka
- `database/` – konekcija sa PostgreSQL bazom, kreiranje tabela i insert logika
- `main` fajl – centralno pokretanje svih scrapera, uključujući paralelan rad
- `README.md` – dokumentacija projekta

Ovakva podela olakšava:

- održavanje koda
- dodavanje novih izvora podataka
- testiranje pojedinačnih komponenti
- prelazak na veće scrape sesije i kasniju analitiku

## Trenutni tok obrade podataka

Tok podataka trenutno izgleda ovako:

1. `main` fajl pokreće sva 3 scrapera paralelno
2. svaki scraper obilazi listing i detaljne stranice svog sajta
3. izvučeni sirovi podaci se prosleđuju u preprocessing pipeline
4. preprocessing čisti i standardizuje vrednosti
5. svaki obrađeni oglas se individualno upisuje u odgovarajuću tabelu baze
6. duplikati se preskaču pomoću `UNIQUE` ograničenja nad URL kolonom i `ON CONFLICT (url) DO NOTHING`

To znači da sistem ne zavisi od ručnog brisanja starih podataka i može bezbedno da se koristi za veće scrape-ove bez pucanja na duplikatima.

## Sledeći logični koraci

Nakon trenutne stabilizacije sistema, prirodni naredni koraci su:

### 1. Masovni scrape
Pokretanje većeg broja stranica i dužih scrape sesija radi punjenja baze većim brojem oglasa.

### 2. Analitika i modelovanje
Kada baza dovoljno poraste, sledeća faza može da uključi:

- eksplorativnu analizu podataka
- vizuelizaciju tržišta nekretnina
- feature engineering
- trening modela za procenu cena

## Napomena

Ovaj projekat je trenutno u fazi izgradnje stabilnog scraping i data ingestion sistema. Fokus je na tome da pipeline bude pouzdan, proširiv i spreman za veći obim podataka pre nego što krene ozbiljnija analitika i modelovanje.

## Sažetak

U ovom trenutku projekat već ima:

- 3 funkcionalna scrapera
- preprocessing pipeline
- PostgreSQL bazu sa odvojenim tabelama
- individualni insert podataka
- zaštitu od duplikata
- paralelno pokretanje sva 3 scrapera iz jednog `main` fajla
- potvrđen rad kroz testiranje za sve ključne komponente

To je vrlo dobra osnova za sledeću fazu: masovno prikupljanje podataka i izgradnju kvalitetnog dataseta za analizu tržišta nekretnina u Srbiji.
