import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
from fastapi.responses import FileResponse

load_dotenv()

engine = create_engine(
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Učitaj modele
lin_reg     = joblib.load("machine_learning/lin_reg.joblib")
rf_residual = joblib.load("machine_learning/rf_residual.joblib")
le          = joblib.load("machine_learning/label_encoder.joblib")
imputer     = joblib.load("machine_learning/imputer.joblib")
encoder     = joblib.load("machine_learning/target_encoder.joblib")

num_cols = [
    "kvadratura", "broj_soba", "sprat", "ukupna_spratnost",
    "sprat_ratio", "amenity_score",
    "mesec_sin", "mesec_cos", "kvartal", "godina",
    "lokacija_encoded",
    "terasa", "parking", "garaza", "lift", "podrum",
    "internet", "klima", "interfon", "video_nadzor", "uknjizen",
]
cat_cols = ["stanje_objekta", "grejanje", "oglasivac", "tip_nekretnine"]

class Stan(BaseModel):
    kvadratura: float
    broj_soba: float
    sprat: float | None = None
    ukupna_spratnost: float | None = None
    amenity_score: float = 0
    mesec_sin: float = 0
    mesec_cos: float = 1
    kvartal: int = 1
    godina: int = 2026
    lokacija: str | None = None
    broj_dana: float = 475
    terasa: float = 0
    parking: float = 0
    garaza: float = 0
    lift: float = 0
    podrum: float = 0
    internet: float = 0
    klima: float = 0
    interfon: float = 0
    video_nadzor: float = 0
    uknjizen: float = 0
    stanje_objekta: str = "Unknown"
    grejanje: str = "Unknown"
    oglasivac: str = "Unknown"
    tip_nekretnine: str = "Unknown"

@app.post("/predict")
def predict(stan: Stan):
    data = stan.model_dump()

    # sprat_ratio
    if data["sprat"] and data["ukupna_spratnost"]:
        data["sprat_ratio"] = data["sprat"] / data["ukupna_spratnost"]
    else:
        data["sprat_ratio"] = np.nan

    # target encoding lokacije
    lokacija_df = pd.DataFrame([{"lokacija": data["lokacija"]}])
    data["lokacija_encoded"] = encoder.transform(lokacija_df)["lokacija"].values[0]

    # numericki featurei
    X_num = pd.DataFrame([{col: data.get(col, np.nan) for col in num_cols}])
    X_num_imp = imputer.transform(X_num)

    # kategoricki featurei
    X_cat = pd.DataFrame([{col: data.get(col, "Unknown") for col in cat_cols}])
    for col in cat_cols:
        known = set(le.classes_)
        X_cat[col] = le.transform(
            X_cat[col].where(X_cat[col].isin(known), "Unknown")
        )

    X = np.hstack([X_num_imp, X_cat.values])

    # hibridna predikcija
    trend    = lin_reg.predict([[data["broj_dana"]]])[0]
    rezidual = rf_residual.predict(X)[0]

    return {"predikcija_eur": round(trend + rezidual, 2)}


@app.post("/slicni")
def slicni(stan: Stan):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT title, price_total, price_per_m2, kvadratura, sprat, ukupna_spratnost, url
            FROM gold.unified_deduplicated
            WHERE kvadratura BETWEEN :kv_min AND :kv_max
              AND broj_soba = :broj_soba
              AND lokacija = :lokacija
              AND price_total IS NOT NULL
            ORDER BY ABS(kvadratura - :kvadratura)
            LIMIT 3
        """), {
            "kv_min":     stan.kvadratura - 10,
            "kv_max":     stan.kvadratura + 10,
            "broj_soba":  stan.broj_soba,
            "lokacija":   stan.lokacija,
            "kvadratura": stan.kvadratura,
        })
        rows = result.fetchall()

    return [
        {
            "title":             row[0],
            "price_total":       row[1],
            "price_per_m2":      round(row[2], 2) if row[2] else None,
            "kvadratura":        row[3],
            "sprat":             row[4],
            "ukupna_spratnost":  row[5],
            "url":               row[6],
        }
        for row in rows
    ]
@app.get("/")
def root():
    return FileResponse("frontend.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)