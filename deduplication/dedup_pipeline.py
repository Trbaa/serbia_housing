import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text, Numeric, Text, Boolean, Date, DateTime, Integer
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

# Eksplicitni tipovi za to_sql — sprečava SQLAlchemy da inferuje TEXT za numeričke kolone
DTYPE_MAP = {
    "price_total":          Numeric(),
    "price_avg":            Numeric(),
    "price_per_m2":         Numeric(),
    "kvadratura":           Numeric(),
    "broj_soba":            Numeric(),
    "sprat":                Numeric(),
    "ukupna_spratnost":     Integer(),
    "uknjizen":             Boolean(),
    "terasa":               Boolean(),
    "interfon":             Boolean(),
    "klima":                Boolean(),
    "video_nadzor":         Boolean(),
    "internet":             Boolean(),
    "parking":              Boolean(),
    "garaza":               Boolean(),
    "lift":                 Boolean(),
    "podrum":               Boolean(),
    "datum_objave":         Date(),
    "created_at":           DateTime(),
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
    (df["price_total"].between(20_000, 3_000_000)) &
    (df["kvadratura"].between(10, 600))
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

print("Klasterujem...")
susedi = {}
for par in kandidati:
    susedi.setdefault(par["oglas_a"], set()).add(par["oglas_b"])
    susedi.setdefault(par["oglas_b"], set()).add(par["oglas_a"])

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

import io
from psycopg2.extras import execute_values

def upisati_u_bazu(df_validni, df, engine):
    print("\nUpisujem u gold.unified_deduplicated...")

    df_full = pd.read_sql("SELECT * FROM gold.unified_oglasi", engine)
    oglas_lookup = {row["oglas_id"]: row.to_dict() for _, row in df_full.iterrows()}

    redovi = []
    for _, red in df_validni.iterrows():
        for oglas_id in red["oglas_ids"]:
            oglas = oglas_lookup.get(oglas_id)
            if oglas is None:
                continue
            oglas = oglas.copy()
            oglas["stan_id"]   = red["stan_id"]
            oglas["price_avg"] = float(red["price_avg"]) if red["price_avg"] is not None else None
            redovi.append(oglas)

    df_upis = pd.DataFrame(redovi)
    df_upis = df_upis.drop(columns=["unified_id"], errors="ignore")

    # --- type conversions (same as before) ---
    NUMERIC_COLS = ["price_total", "price_avg", "price_per_m2", "kvadratura", "broj_soba", "sprat"]
    for col in NUMERIC_COLS:
        if col in df_upis.columns:
            df_upis[col] = pd.to_numeric(df_upis[col], errors="coerce")

    if "ukupna_spratnost" in df_upis.columns:
        df_upis["ukupna_spratnost"] = pd.to_numeric(
            df_upis["ukupna_spratnost"], errors="coerce"
        ).astype("Int64")

    BOOL_COLS = ["uknjizen", "terasa", "interfon", "klima",
                 "video_nadzor", "internet", "parking", "garaza", "lift", "podrum"]
    for col in BOOL_COLS:
        if col in df_upis.columns:
            df_upis[col] = df_upis[col].where(df_upis[col].notna(), None)
            df_upis[col] = df_upis[col].map(lambda x: bool(x) if x is not None else None)

    df_upis = df_upis.where(pd.notna(df_upis), None)

    kolone = list(df_upis.columns)
    kolone_str = ", ".join(kolone)

    # Serialize DataFrame to CSV in memory — no disk I/O
    buffer = io.StringIO()
    df_upis.to_csv(buffer, index=False, header=False, na_rep="\\N")
    buffer.seek(0)

    with engine.connect() as conn:
        raw_conn = conn.connection
        cursor = raw_conn.cursor()

        # 1. Temp table with same structure, auto-dropped at end of session
        cursor.execute(f"""
            CREATE TEMP TABLE tmp_dedup (LIKE gold.unified_deduplicated INCLUDING ALL)
            ON COMMIT DROP
        """)

        # 2. COPY CSV buffer directly into temp table — fastest possible load
        cursor.copy_expert(f"""
            COPY tmp_dedup ({kolone_str})
            FROM STDIN WITH (FORMAT csv, NULL '\\N')
        """, buffer)

        # 3. Upsert from temp into real table in one SQL statement
        update_set = ", ".join([
            f"{col} = EXCLUDED.{col}"
            for col in ["lokacija", "price_avg", "stan_id"]
        ])
        cursor.execute(f"""
            INSERT INTO gold.unified_deduplicated ({kolone_str})
            SELECT {kolone_str} FROM tmp_dedup
            ON CONFLICT (oglas_id) DO UPDATE SET {update_set}
        """)

        raw_conn.commit()
        print(f"Upisano: {len(df_upis)} redova")
upisati_u_bazu(df_validni, df, engine)