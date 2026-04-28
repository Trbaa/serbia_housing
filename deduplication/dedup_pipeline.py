import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.preprocessing import MinMaxScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import sys
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.aws"))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_config import get_scraping_db_connection_params

# ── KONSTANTE ─────────────────────────────────────────────────────────────────

PRAG        = 0.92
MAX_CV      = 0.10
MAX_CLUSTER = 10
MAX_KV_DIFF = 5

TEZINE = {
    "kvadratura":   0.25,
    "price_per_m2": 0.25,
    "broj_soba":    0.15,
    "sprat":        0.05,
    "lokacija":     0.05,
    "tekst":        0.25,
}

# ── KONEKCIJA ─────────────────────────────────────────────────────────────────

def get_engine():
    params = get_scraping_db_connection_params()
    url = (
        f"postgresql+psycopg2://{params['user']}:{params['password']}"
        f"@{params['host']}:{params['port']}/{params['database']}"
    )
    return create_engine(url, connect_args={"options": "-c search_path=gold,silver,public"})

engine = get_engine()

# ── UČITAVANJE I FILTRIRANJE ──────────────────────────────────────────────────

df = pd.read_sql("""
    SELECT oglas_id, izvor, url, lokacija, kvadratura, broj_soba,
           sprat, price_total, dodatni_opis,
           CASE WHEN price_total > 0 AND kvadratura > 0
                THEN price_total / kvadratura END AS price_per_m2_calc
    FROM gold.unified_oglasi
    WHERE kvadratura IS NOT NULL AND price_total IS NOT NULL AND broj_soba IS NOT NULL
""", engine)

df = df[
    (df["price_total"].between(20_000, 2_000_000)) &
    (df["kvadratura"].between(15, 400))
].copy()

print(f"Učitano: {len(df)} oglasa")

# ── NORMALIZACIJA ─────────────────────────────────────────────────────────────

scaler = MinMaxScaler()
df["kv_norm"]    = scaler.fit_transform(df[["kvadratura"]])
df["sobe_norm"]  = scaler.fit_transform(df[["broj_soba"]])
df["sprat_norm"] = scaler.fit_transform(df[["sprat"]].fillna(0))
df["ppm2_norm"]  = scaler.fit_transform(df[["price_per_m2_calc"]])

# ── TF-IDF ────────────────────────────────────────────────────────────────────

print("Računam TF-IDF...")
df["opis_clean"] = df["dodatni_opis"].fillna("").str.lower().str.strip()
tfidf_matrix = TfidfVectorizer(min_df=2, max_df=0.95, ngram_range=(1, 2)).fit_transform(df["opis_clean"])
oglas_id_to_idx = {oglas_id: idx for idx, oglas_id in enumerate(df["oglas_id"])}

# ── SCORE FUNKCIJA ────────────────────────────────────────────────────────────

def score(row_a, row_b):
    lok   = 1.0 if row_a["lokacija"] == row_b["lokacija"] else 0.0
    kv    = 1 - abs(row_a["kv_norm"]    - row_b["kv_norm"])
    sobe  = 1 - abs(row_a["sobe_norm"]  - row_b["sobe_norm"])
    sprat = 1 - abs(row_a["sprat_norm"] - row_b["sprat_norm"])
    ppm2  = 1 - abs(row_a["ppm2_norm"]  - row_b["ppm2_norm"])
    tekst = float(cosine_similarity(
        tfidf_matrix[oglas_id_to_idx[row_a["oglas_id"]]],
        tfidf_matrix[oglas_id_to_idx[row_b["oglas_id"]]]
    )[0][0])

    if tekst > 0.95:
        return 1.0

    return (
        TEZINE["kvadratura"]   * kv    +
        TEZINE["price_per_m2"] * ppm2  +
        TEZINE["broj_soba"]    * sobe  +
        TEZINE["sprat"]        * sprat +
        TEZINE["lokacija"]     * lok   +
        TEZINE["tekst"]        * tekst
    )

# ── KANDIDAT PAROVI ───────────────────────────────────────────────────────────

print("Tražim kandidat parove...")
kandidati = []

for lokacija, grupa in df.groupby("lokacija"):
    if lokacija == "Nepoznato" or len(grupa) < 2:
        continue
    grupa = grupa.sort_values("kvadratura").reset_index(drop=True)
    for i in range(len(grupa)):
        for j in range(i + 1, len(grupa)):
            row_a, row_b = grupa.iloc[i], grupa.iloc[j]
            if abs(row_a["kvadratura"] - row_b["kvadratura"]) > MAX_KV_DIFF:
                break
            if row_a["izvor"] == row_b["izvor"]:
                continue
            s = score(row_a, row_b)
            if s >= PRAG:
                kandidati.append({"oglas_a": row_a["oglas_id"], "oglas_b": row_b["oglas_id"], "score": round(s, 3)})

print(f"Pronađeno kandidat parova: {len(kandidati)}")

# ── CLUSTERING ────────────────────────────────────────────────────────────────

print("Klasterijem...")
susedi = {}
for par in kandidati:
    susedi.setdefault(par["oglas_a"], set()).add(par["oglas_b"]) # ukoliko oglas_a ne postoji u recniku dodaj ga kao prazan i stavi mu par b
    susedi.setdefault(par["oglas_b"], set()).add(par["oglas_a"]) #ista prica

poseceni, klasteri = set(), []
for oglas_id in df["oglas_id"]:
    if oglas_id in poseceni:
        continue
    klaster = {oglas_id}
    poseceni.add(oglas_id)
    for kandidat in susedi.get(oglas_id, set()) - poseceni:
        if all(kandidat in susedi.get(clan, set()) for clan in klaster):
            klaster.add(kandidat)
            poseceni.add(kandidat)
    klasteri.append(klaster)

print(f"Ukupno klastera: {len(klasteri)}")

# ── REZULTATI ─────────────────────────────────────────────────────────────────

rezultati = []
for stan_id, komponenta in enumerate(klasteri):
    oglasi = df[df["oglas_id"].isin(komponenta)]
    cene   = oglasi["price_total"].dropna()

    if len(komponenta) > MAX_CLUSTER:
        for oglas_id in komponenta:
            rezultati.append({"stan_id": f"solo_{oglas_id}", "oglas_ids": [oglas_id],
                               "n_oglasa": 1, "price_avg": df[df["oglas_id"] == oglas_id].iloc[0]["price_total"],
                               "price_cv": None, "odbacen": "preveliki_klaster"})
        continue

    if len(cene) > 1 and (cene.std() / cene.mean()) > MAX_CV:
        for oglas_id in komponenta:
            rezultati.append({"stan_id": f"solo_{oglas_id}", "oglas_ids": [oglas_id],
                               "n_oglasa": 1, "price_avg": df[df["oglas_id"] == oglas_id].iloc[0]["price_total"],
                               "price_cv": None, "odbacen": "velika_varijacija_cene"})
        continue

    rezultati.append({
        "stan_id":   f"stan_{stan_id:06d}",
        "oglas_ids": list(komponenta),
        "n_oglasa":  len(komponenta),
        "price_avg": round(cene.mean(), 2),
        "price_cv":  round(cene.std() / cene.mean(), 3) if len(cene) > 1 else None,
        "odbacen":   None,
    })

df_rezultati = pd.DataFrame(rezultati)
df_validni   = df_rezultati[df_rezultati["odbacen"].isna()]
df_odbaceni  = df_rezultati[df_rezultati["odbacen"].notna()]

# ── STATISTIKE ────────────────────────────────────────────────────────────────

print(f"\n{'='*50}")
print(f"Jedinstvenih stanova:       {len(df_validni)}")
print(f"Stanova sa 2+ oglasa:       {len(df_validni[df_validni['n_oglasa'] > 1])}")
print(f"Stanova sa 3+ oglasa:       {len(df_validni[df_validni['n_oglasa'] > 2])}")
print(f"Odbacenih — preveliki:      {len(df_odbaceni[df_odbaceni['odbacen'] == 'preveliki_klaster'])}")
print(f"Odbacenih — varijacija:     {len(df_odbaceni[df_odbaceni['odbacen'] == 'velika_varijacija_cene'])}")
print(f"{'='*50}")

"""
# ── VALIDACIJA — 20 NASUMIČNIH PAROVA ────────────────────────────────────────

print("\nValidacija — 20 nasumičnih parova sa 2 oglasa:")
pd.set_option("display.max_colwidth", None)

for _, red in df_validni[df_validni["n_oglasa"] == 2].sample(20, random_state=123).iterrows():
    oglasi = df[df["oglas_id"].isin(red["oglas_ids"])]
    print(f"\nstan_id: {red['stan_id']} | price_avg: {red['price_avg']} | cv: {red['price_cv']}")
    print(oglasi[["izvor", "lokacija", "kvadratura", "broj_soba", "sprat", "price_total", "url"]].to_string(index=False))
    print("Opisi:")
    for _, oglas in oglasi.iterrows():
        print(f"  [{oglas['izvor']}]: {str(oglas['dodatni_opis'])[:150]}")
    print("-" * 80)
"""
# ── UPIS U BAZU ───────────────────────────────────────────────────────────────

def upisati_u_bazu(df_validni, df, engine):
    print("\nUpisujem u gold.unified_deduplicated...")

    df_full = pd.read_sql("SELECT * FROM gold.unified_oglasi", engine)

    redovi = []
    for _, red in df_validni.iterrows():
        for oglas_id in red["oglas_ids"]:
            oglas = df_full[df_full["oglas_id"] == oglas_id]
            if oglas.empty:
                continue
            oglas = oglas.iloc[0].to_dict()
            oglas["stan_id"]   = red["stan_id"]
            oglas["price_avg"] = red["price_avg"]
            redovi.append(oglas)

    df_upis = pd.DataFrame(redovi)
    df_upis = df_upis.drop(columns=["unified_id"], errors="ignore")

    # Upiši u temp tabelu
    df_upis.to_sql(
        "_dedup_temp", engine, schema="gold",
        if_exists="replace", index=False, chunksize=500
    )

    # INSERT iz temp → prava tabela, preskoči postojeće
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO gold.unified_deduplicated
            SELECT * FROM gold._dedup_temp
            ON CONFLICT (oglas_id) DO NOTHING
        """))
        conn.execute(text("DROP TABLE gold._dedup_temp"))

    print(f"Obradjeno: {len(df_upis)} redova")

# Poziv na kraju
from sqlalchemy import text
upisati_u_bazu(df_validni, df, engine)