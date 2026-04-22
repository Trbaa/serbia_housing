import pandas as pd
import numpy as np
import re

def _normalize(text:str) -> str:
    zamene = {
        'č': 'c', 'ć': 'c', 'š': 's', 'ž': 'z', 'đ': 'd',
        'Č': 'c', 'Ć': 'c', 'Š': 's', 'Ž': 'z', 'Đ': 'd',
    }
    text = text.lower()
    for origin,repl in zamene.items():
        text = text.replace(origin,repl)
    return text

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
    "Zeleznik", "Altina", "Borca", "Krnjaca", "Kotez",
    "Batajnica", "Bezanijska Kosa", "Bezanijska Kosa 1",
    "Bezanijska Kosa 2", "Bezanijska Kosa 3",
    "Blok 1", "Blok 2", "Blok 3", "Blok 4", "Blok 7",
    "Blok 21", "Blok 22", "Blok 23", "Blok 28", "Blok 29",
    "Blok 30", "Blok 33", "Blok 37", "Blok 38",
    "Blok 44", "Blok 45", "Blok 61", "Blok 62",
    "Blok 63", "Blok 64", "Blok 70", "Blok 70A",
    "Blok 72", "Blok 73",

    # Česta mikro-naselja / zone
    "Avala", "Filmski Grad", "Vidikovac", "Petlovo Brdo",
    "Labudovo Brdo", "Kanarevo Brdo", "Miljakovac",
    "Miljakovac 1", "Miljakovac 2", "Miljakovac 3",
    "Resnik", "Kijevo", "Zarkovo", "Julino Brdo",
    "Kosutnjak", "Topcider", "Autokomanda",
    "Slavija", "Kalemegdan", "Dorcol",
    "Donji Dorcol", "Gornji Dorcol",
    "Crveni Krst", "Cvetkova Pijaca",
    "Lion", "Gradska Bolnica", "Djeram",
    "Hadzipopovac", "Bogoslovija",
    "Visnjicka Banja", "Visnjica",
    "Rospi Cuprija", "Ada Huja",
    "Krnjača Most", "Ovca", "Padinska Skela",
    "Borča Greda", "Borča 3",

    # Zemun / NBG dodatno
    "Zemun Polje", "Nova Galenika", "Galenika",
    "Pregrevica", "Gornji Grad", "Donji Grad",
    "Retenzija", "Ledine", "Surcinsko Polje",

    # Južni deo grada
    "Jajinci", "Pinosava", "Beli Potok",
    "Ripanj", "Zuce", "Vrčin", "Leštane",
    "Kaluđerica",

    # Ostalo često u oglasima
    "Stepa Stepanovic", "Brace Jerkovic",
    "Medakovic", "Medakovic 1", "Medakovic 2", "Medakovic 3",
    "Dušanovac", "Dušanovac Pošta",
    "Voždovačka Crkva",
    "Učiteljsko Naselje", "Konjarnik 2",
    "Plavi Horizonti", "Altina 2"
], key=len, reverse=True)

def clean_lokacija(item):
    def extract(text):
        if not text or str(text) in ('nan','None',''):
            return None
        normalizovan = _normalize(str(text))
        for lokacija in LOKACIJE:
            pattern = r'\b' + re.escape(_normalize(lokacija)) + r'\b'
            if re.search(pattern,normalizovan):
                return lokacija
        return None
    result = extract(item['title'].iloc[0]) or extract(item['Dodatni opis'].iloc[0])
    item['lokacija'] = result if result else 'Nepoznato'
    return item

def normalize_missing_df(df):
    return df.replace({
        'Nan': np.nan,
        'NaN': np.nan,
        'None': np.nan,
        '': np.nan,
        ' ': np.nan
    })

def convert_to_python_types(item):
    for col, value in item.items():
        if pd.isna(value):
            item[col] = None
        elif isinstance(value, np.integer):
            item[col] = int(value)
        elif isinstance(value, np.floating):
            item[col] = float(value)
        elif isinstance(value, np.bool_):
            item[col] = bool(value)

    return item

def clean_title(item):
    item["title"] = item["title"].str.replace(r"\d+|EUR|€/m²|€|m²|m2|\.", "", regex=True).str.strip()
    item["title"] = item['title'].str.replace(r", ,","",regex = True).str.strip()
    item["title"] = item['title'].str.strip(",")

    return item

def clean_price_total(item):
    item["price_total"] = (
    item["price_total"]
    .astype("string")
    .str.split("\n").str[0]
    .str.lower()
    .str.replace(r"od\s*", "", regex=True)
   .str.replace(r"eur|€|rsd|din|evra|eura", "", regex=True)
    .str.replace(r"[.,\s]", "", regex=True)
    .str.replace(r"od ", "", regex=True)
    .str.replace(r"[^\d]", "", regex=True)
    .str.strip()

    )
    item["price_total"] = pd.to_numeric(item["price_total"], errors="coerce").astype("Int64")
    return item

def clean_price_per_m2(item):
    item["price_per_m2"] = (
        item["price_per_m2"]
        .astype("string")
        .str.split("\n").str[0]
        .str.replace(r"od\s+", "", regex=True)
        .str.replace(r"[^\d]", "", regex=True)
    )

    item["price_per_m2"] = pd.to_numeric(item["price_per_m2"], errors="coerce").astype("Int64")
    return item

def clean_tip_nekretnine(item):
    item["Tip nekretnine"] = np.where(
    item["Tip nekretnine"].str.lower().str.contains("stan",na = False),
    "stan",
        np.where(item["Tip nekretnine"].str.lower().str.contains("kuca|kuća",na = False),
            "kuća",
    None
    ))
    return item

def clean_kvadratura(item):
    item["Kvadratura"] = (
        item["Kvadratura"]
        .astype("string")
        .str.lower()
        .str.replace(",", ".", regex=False)
        .str.extract(r"(\d+(?:\.\d+)?)", expand=False)
    )

    item["Kvadratura"] = pd.to_numeric(item["Kvadratura"], errors="coerce")
    return item

def clean_br_soba(item):
    item['Broj soba'] = (
        item['Broj soba']
        .astype('string')
        .str.lower()
        .str.replace(',', '.', regex=False)
        .str.extract(r'(\d+(?:\.\d+)?)', expand=False)
    )

    item['Broj soba'] = pd.to_numeric(item['Broj soba'], errors='coerce')
    return item

def clean_tip_objekta(item):

    item['Tip objekta'] = item['Tip objekta'].astype('object')
    item.loc[
    item['Tip objekta'].isna() &
    item['Stanje objekta'].isin(['Kompletna rekonstrukcija','Renovirano']),
    'Tip objekta'
] = 'Stara_gradnja'

    item.loc[
    item['Tip objekta'].isna() &
    item['Stanje objekta'].isin(['Novo', 'Lux']),
    'Tip objekta'
] = 'Novo_gradnja'
    
    item['Tip objekta'] = item['Tip objekta'].replace({
    'Stara gradnje': 'Stara_gradnja',
    'Novogradnja': 'Novo_gradnja'
})

    return item

def clean_stanje_obj(item):
    item['Stanje objekta'] = item['Stanje objekta'].replace('Izvorno stanje','Izvorno_stanje')
    return item

def clean_grejanje(item):
    item['Grejanje'] = (
    item['Grejanje']
    .astype('string')
    .str.replace(r"Grejanje:\s*", "", regex=True)
    .str.replace(r"\bKlima uređaj\b|\bKlima uredjaj\b", "Klima", regex=True)
    .str.replace(r"\bOstalo\b", "", regex=True)
    .str.replace(r"\s*,\s*", ", ", regex=True)
    .str.replace(r"^,\s*|\s*,$", "", regex=True)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)
    
    item['Grejanje'] = (
    item['Grejanje']
    .str.replace(r"\bCentralno grejanje\b", "centralno", regex=True)
    .str.replace(r"\bPodno grejanje\b", "podno", regex=True)
    .str.replace(r"\bToplotna pumpa\b", "toplotna_pumpa", regex=True)
    .str.replace(r"\bEtažno grejanje na struju\b", "etazno_struja", regex=True)
    .str.replace(r"\bEtažno grejanje na gas\b", "etazno_gas", regex=True)
    .str.replace(r"\bEtažno grejanje na čvrsto gorivo\b|\bEtažno grejanje na cvrsto gorivo\b", "etazno_cvrsto_gorivo", regex=True)
    .str.replace(r"\bKlima\b", "klima", regex=True)
)
    
    item['Grejanje'] = item['Grejanje'].str.replace(r",\s*$", "", regex=True)

    return item

def clean_sprat(item):
    roman_map = {
        "i": "1",
        "ii": "2",
        "iii": "3",
        "iv": "4",
        "v": "5",
        "vi": "6",
        "vii": "7",
        "viii": "8",
        "ix": "9",
        "x": "10",
        "xi": "11",
        "xii": "12",
        "xiii": "13",
        "xiv": "14",
        "xv": "15",
    }

    item["Sprat"] = (
        item["Sprat"]
        .astype("string")
        .str.strip()
        .str.lower()
        .replace({
            "visoko prizemlje": "0.5",
            "prizemlje": "0",
            "suteren": "-0.5",
            "suturen": "-0.5",
            "vpr": "0.5",
            "pr": "0",
            "p": "0",
        })
        .str.replace(",", ".", regex=False)
        .str.replace(r"\bsprat\b", "", regex=True)
        .str.strip()
    )

    for roman, arabic in sorted(roman_map.items(), key=lambda x: len(x[0]), reverse=True):
        item["Sprat"] = item["Sprat"].str.replace(
            rf"\b{roman}\b", arabic, regex=True
        )

    item["Sprat"] = item["Sprat"].str.extract(r"(-?\d+(?:\.\d+)?)", expand=False)
    item["Sprat"] = pd.to_numeric(item["Sprat"], errors="coerce")

    return item

def clean_uk_sprat(item):
    item["Ukupna spratnost"] = (
        item["Ukupna spratnost"]
        .astype("string")
        .str.strip()
        .str.extract(r"(\d+)", expand=False)
    )

    item["Ukupna spratnost"] = pd.to_numeric(item["Ukupna spratnost"], errors="coerce")
    return item

def clean_opis(item):
    #Sredjivanje Dodatni opis - ovo isto treba mnogo ranije da se uradi jer se odavde vade featursi
    item['Dodatni opis'] = (
    item['Dodatni opis']
    .astype('string')
    # linkovi
    .str.replace(r'http\S+|www\.\S+', '', regex=True)
    # procenti, npr. 2%, 3.5 %
    .str.replace(r'\b\d+(?:[.,]\d+)?\s*%', '', regex=True)
    # brojevi telefona: 060/123-4567, 011/123-456, +381 60 123 45 67 itd.
    .str.replace(r'(?:tel(?:efon)?i?\s*:?\s*)?(?:\+381|0)\s*\d(?:[\d\s/\-•()]*)\d', '', regex=True)
    .str.replace(r'Više informacija na:\s*', '', regex=True)
    .str.replace(r'Agencijska provizija\.?\s*', '', regex=True)
    .str.replace(r'Telefoni?:\s*', '', regex=True)
    .str.replace(r'Kontakt van radnog vremena:\s*', '', regex=True)
    .str.replace(r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b', '', regex=True)
    .str.replace(r'Agencijski\s*ID\s*:\s*\d+\s*,?\s*', '', regex=True)
    .str.replace(r'Oglas\s*ID\s*:\s*\d+\s*,?\s*', '', regex=True)
    # višestruki razmaci
    .str.replace(r'\s+', ' ', regex=True)
    # razmaci oko tačke i zareza
    .str.replace(r'\s+([,.:;])', r'\1', regex=True)
    .str.strip()
    )
    return item

def clean_uknjizen(item):
    item['Uknjižen'] = item['Uknjižen'].replace({
    'da': True,
    'ne': False})

    opis = item['Dodatni opis'].astype('string').str.lower()

    neg_mask = opis.str.contains(
    r'nije\s+uknjižen|nije\s+uknjizen|'
    r'biće\s+uknjižen|bice\s+uknjizen|'
    r'uskoro\s+uknjižen|uskoro\s+uknjizen|'
    r'u\s+procesu\s+uknjiženja|u\s+procesu\s+uknjizenja|'
    r'predat[ao]?\s+za\s+uknjiženje|predat[ao]?\s+za\s+uknjizenje|'
    r'može\s+uknjiženje|moze\s+uknjizenje|'
    r'zgrada\s+je\s+uknjižena|zgrada\s+je\s+uknjizena|'
    r'objekat\s+je\s+uknjižen|objekat\s+je\s+uknjizen',
    regex=True,
    na=False
)

    pos_mask = opis.str.contains(
    r'uknjižen\s+na|uknjizen\s+na|'
    r'uknjižena\s+površina|uknjizena\s+povrsina|'
    r'uknjiženo\s+\d+|uknjizeno\s+\d+|'
    r'stan\s+je\s+uknjižen|stan\s+je\s+uknjizen|'
    r'uknjižen\s+je|uknjizen\s+je|'
    r'uknjižena\s+je|uknjizena\s+je|'
    r'\buknjižen\b|\buknjizen\b',
    regex=True,
    na=False
)

    item.loc[
        item['Uknjižen'].isna() & pos_mask & ~neg_mask,
        'Uknjižen'
    ] = True

    return item

def clean_terasa(item):
    item['Terasa'] = item['Terasa'].replace({
    'da': 1,
    'ne': 0})
    item['Terasa'] = pd.to_numeric(item['Terasa'], errors='coerce')

    opis = item['Dodatni opis'].astype('string').str.lower()

    neg_mask = opis.str.contains(
    r'bez\s+terase|bez\s+terasa|nema\s+terasu|nema\s+terase|bez\s+lođe|bez\s+lođa|bez\s+lodje|bez\s+lodja',
    regex=True,
    na=False
)

    pos_mask = opis.str.contains(
    r'\bterasa\b|\bterase\b|\blođa\b|\blođe\b|\blodja\b|\blodje\b',
    regex=True,
    na=False
)

    item.loc[
    item['Terasa'].isna() & pos_mask & ~neg_mask,
    'Terasa'
] = 1

    item.loc[
    item['Terasa'].isna() & neg_mask,
    'Terasa'
] = 0
    item['Terasa'] = item['Terasa'].map({1: True, 0: False}).astype('boolean')

    return item

def clean_interfon(item):
    #Interfon
    item['Interfon'] = item['Interfon'].map({'da': True, 'ne': False}).astype('boolean')
    item.loc[
    item['Interfon'].isna() &
    (item['Tip objekta'] == 'Novo_gradnja'),
    'Interfon'
    ] = True

    opis = item['Dodatni opis'].astype('string').str.lower()

    neg_mask = opis.str.contains(
    r'bez\s+interfona|nema\s+interfon|bez\s+interfonske\s+veze',
    regex=True,
    na=False
    )

    pos_mask = opis.str.contains(
    r'\binterfon\b|\binterfonsk\w*\b|\bvideo\s+interfon\b',
    regex=True,
    na=False
    )

    item.loc[
    item['Interfon'].isna() & pos_mask & ~neg_mask,
    'Interfon'
    ] = True

    item.loc[
    item['Interfon'].isna() & neg_mask,
    'Interfon'
    ] = False
    
    return item

def clean_klima(item):
    #Klima
    item['Klima'] = item['Klima'].map({'da': True, 'ne': False}).astype('boolean')

    opis = item['Dodatni opis'].astype('string').str.lower()

    neg_mask = opis.str.contains(
    r'bez\s+klime|nema\s+klimu|nije\s+ugrađena\s+klima|nije\s+ugradjena\s+klima',
    regex=True,
    na=False
    )

    pos_mask = opis.str.contains(
    r'\bklima\b|\bklime\b|\bklima uređaj\b|\bklima uredjaj\b|\bklimatizovan\b|\bklimatizirana\b',
    regex=True,
    na=False
    )

    item.loc[
    item['Klima'].isna() & pos_mask & ~neg_mask,
    'Klima'
    ] = True

    item.loc[
    item['Klima'].isna() & neg_mask,
    'Klima'
    ] = False    

    return item

def clean_video_nadzor(item):
    #Video nadzor
#Klima
    item['Video nadzor'] = item['Video nadzor'].map({'da': True, 'ne': False}).astype('boolean')

    opis = item['Dodatni opis'].astype('string').str.lower()

    neg_mask = opis.str.contains(
    r'bez\s+video\s+nadzora|'
    r'nema\s+video\s+nadzor|'
    r'bez\s+nadzornih\s+kamera|'
    r'nema\s+kamere|'
    r'bez\s+kamere|'
    r'bez\s+nadzora',
    regex=True,
    na=False
    )

    pos_mask = opis.str.contains(
    r'\bvideo\s*nadzor\b|'
    r'\bvideo-nadzor\b|'
    r'\bnadzorne?\s+kamere\b|'
    r'\bkamere\b|'
    r'\bkamera\b',
    regex=True,
    na=False
    )

    item.loc[
    item['Video nadzor'].isna() & pos_mask & ~neg_mask,
    'Video nadzor'
    ] = True

    item.loc[
    item['Video nadzor'].isna() & neg_mask,
    'Video nadzor'
    ] = False

    return item

def clean_internet(item):
        #Internet
    item['Internet'] = item['Internet'].map({'da': True, 'ne': False}).astype('boolean')

    opis = item['Dodatni opis'].astype('string').str.lower()

    neg_mask = opis.str.contains(
    r'bez\s+interneta|nema\s+internet|bez\s+internet priključka|bez\s+internet prikljucka',
    regex=True,
    na=False
    )

    pos_mask = opis.str.contains(
    r'\binternet\b|\bwi[\s\-]?fi\b|\boptički internet\b|\bopticki internet\b|\bkablovski internet\b',
    regex=True,
    na=False
    )

    item.loc[
    item['Internet'].isna() & pos_mask & ~neg_mask,
    'Internet'
    ] = True

    item.loc[
    item['Internet'].isna() & neg_mask,
    'Internet'
    ] = False

    return item

def clean_parking(item):
#parking
    item['Parking'] = item['Parking'].map({'da': True,'ne': False}).astype('boolean')


    opis = item['Dodatni opis'].astype('string').str.lower()

    neg_mask = opis.str.contains(
    r'bez\s+parkinga|'
    r'nema\s+parking|'
    r'bez\s+parking mesta|'
    r'bez\s+parking mesta|'
    r'bez\s+parkinga\s+i\s+garaže|'
    r'bez\s+parkinga\s+i\s+garaze',
    regex=True,
    na=False
    )

    pos_mask = opis.str.contains(
    r'\bparking\b|'
    r'\bparking mesto\b|'
    r'\bparking mesta\b|'
    r'\bparking prostor\b|'
    r'\bparking uz zgradu\b|'
    r'\bobezbeđen parking\b|'
    r'\bobezbedjen parking\b|'
    r'\bslobodan parking\b|'
    r'\bparking ispred zgrade\b',
    regex=True,
    na=False
    )

    item.loc[
    item['Parking'].isna() & pos_mask & ~neg_mask,
    'Parking'
    ] = True

    item.loc[
    item['Parking'].isna() & neg_mask,
    'Parking'
    ] = False

    return item

def clean_garaza(item):
    item['Garaža'] = item['Garaža'].map({'da': True,'ne':False}).astype('boolean')

    opis = item['Dodatni opis'].astype('string').str.lower()

    neg_mask = opis.str.contains(
    r'bez\s+garaže|'
    r'bez\s+garaze|'
    r'nema\s+garažu|'
    r'nema\s+garazu|'
    r'bez\s+garažnog\s+mesta|'
    r'bez\s+garaznog\s+mesta',
    regex=True,
    na=False
    )

    pos_mask = opis.str.contains(
    r'\bgaraža\b|'
    r'\bgaraza\b|'
    r'\bgaražno\s+mesto\b|'
    r'\bgarazno\s+mesto\b|'
    r'\bgaraža\s+u\s+zgradi\b|'
    r'\bgaraza\s+u\s+zgradi\b|'
    r'\bgaražno\s+mesto\b|'
    r'\bgarazno\s+mesto\b',
    regex=True,
    na=False
    )

    item.loc[
    item['Garaža'].isna() & pos_mask & ~neg_mask,
    'Garaža'
    ] = True

    item.loc[
    item['Garaža'].isna() & neg_mask,
    'Garaža'
    ] = False

    return item

def clean_lift(item):
    
    item['Lift'] = item['Lift'].map({'da': True,'ne':False}).astype('boolean')

    opis = item['Dodatni opis'].astype('string').str.lower()

    neg_mask = opis.str.contains(
        r'bez\s+lifta|'
        r'nema\s+lift',
        regex=True,
        na=False
    )

    pos_mask = opis.str.contains(
        r'\blift\b|\bliftom\b|\blifta\b',
        regex=True,
        na=False
    )

    item.loc[
        item['Lift'].isna() & pos_mask & ~neg_mask,
        'Lift'
    ] = True

    item.loc[
        item['Lift'].isna() & neg_mask,
        'Lift'
    ] = False

    return item

def clean_podrum(item):
    item['Podrum'] = item['Podrum'].map({'da': True,'ne':False}).astype('boolean')

    opis = item['Dodatni opis'].astype('string').str.lower()

    neg_mask = opis.str.contains(
        r'bez\s+podruma|'
        r'nema\s+podrum|'
        r'bez\s+pripadajućeg\s+podruma|'
        r'bez\s+pripadajuceg\s+podruma',
        regex=True,
        na=False
    )

    pos_mask = opis.str.contains(
        r'\bpodrum\b|'
        r'\bpodrumska\s+prostorija\b|'
        r'\bpripadajući\s+podrum\b|'
        r'\bpripadajuci\s+podrum\b',
        regex=True,
        na=False
    )

    item.loc[
        item['Podrum'].isna() & pos_mask & ~neg_mask,
        'Podrum'
    ] = True

    item.loc[
        item['Podrum'].isna() & neg_mask,
        'Podrum'
    ] = False

    return item

def clean_datum_objave(item):
    col = "Datum_objave"

    if col not in item.columns:
        return item

    s = item[col].astype("string")

    s = s.str.replace(r"^\[|\]$", "", regex=True)
    s = s.str.replace(r"'", "", regex=True)
    s = s.str.split(r"\s+u\s+").str[0]
    s = s.str.replace(r"^Objavljen:\s*", "", regex=True)
    s = s.str.strip()

    # skini završnu tačku ako postoji: 11.04.2026. -> 11.04.2026
    s = s.str.replace(r"\.$", "", regex=True)

    item[col] = pd.to_datetime(
        s,
        format="%d.%m.%Y",
        errors="coerce"
    ).dt.date

    return item

def preprocess(item):
    item = pd.DataFrame([item])
    item = normalize_missing_df(item)

    item = clean_title(item)
    item = clean_price_total(item)
    item = clean_price_per_m2(item)
    item = clean_tip_nekretnine(item)
    item = clean_kvadratura(item)
    item = clean_br_soba(item)
    item = clean_tip_objekta(item)
    item = clean_stanje_obj(item)
    item = clean_grejanje(item)
    item = clean_sprat(item)
    item = clean_uk_sprat(item)
    item = clean_opis(item)
    item = clean_lokacija(item)
    item = clean_uknjizen(item)
    item = clean_terasa(item)
    item = clean_interfon(item)
    item = clean_klima(item)
    item = clean_video_nadzor(item)
    item = clean_internet(item)
    item = clean_parking(item)
    item = clean_garaza(item)
    item = clean_lift(item)
    item = clean_podrum(item)
    item = clean_datum_objave(item)

    item = item.iloc[0].to_dict()
    item = convert_to_python_types(item)
    
    return item