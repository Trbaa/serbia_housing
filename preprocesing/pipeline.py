import pandas as pd
import numpy as np


def normalize_missing_df(df):
    return df.replace({
        'Nan': np.nan,
        'NaN': np.nan,
        'None': np.nan,
        '': np.nan,
        ' ': np.nan
    })

def clean_title(item):
    item["title"] = item["title"].str.replace(r"\d+|EUR|€/m²|€|m²|m2|\.", "", regex=True).str.strip()
    item["title"] = item['title'].str.replace(r", ,","",regex = True).str.strip()
    item["title"] = item['title'].str.strip(",")

    return item

def clean_price_total(item):
    item["price_total"] = (
    item["price_total"]
    .str.split("\n").str[0]
    .str.replace(r"EUR|eur|€|RSD|rsd|DIN|din|Evra|evra|Eura|eura", "", regex=True)
    .str.replace(r"[.,\s]", "", regex=True)
    .str.replace(r"od ", "", regex=True)
    .str.strip()
    .astype("Int64")

    )
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
    item["Kvadratura"] = item["Kvadratura"].str.replace(r"m2|m²|kvadrata|~|oko|","",regex = True).str.strip()
    item["Kvadratura"] = item["Kvadratura"].str.replace(r",",".",regex = True).str.strip()
    item["Kvadratura"] = item["Kvadratura"].astype(float)

    return item

def clean_br_soba(item):
    item['Broj soba'] = item['Broj soba'].astype(float)
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
    item['Sprat'] = item['Sprat'].replace({
    'Visoko prizemlje': '0.5',
    'Prizemlje': '0',
    'Suturen': '-0.5'
})
    item['Sprat'] = pd.to_numeric(item['Sprat'], errors='coerce')
    return item

def clean_uk_sprat(item):
    item['Ukupna spratnost'] = (
    item['Ukupna spratnost']
    .astype('string')
    .str.strip()
    .str.extract(r'(\d+)', expand=False)
)

    item['Ukupna spratnost'] = pd.to_numeric(item['Ukupna spratnost'], errors='coerce')
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
    'da': 1,
    'ne': 0})
    item['Uknjižen'] = pd.to_numeric(item['Uknjižen'], errors='coerce')

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
    ] = 1

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

def clean_topla_voda(item):

    item['Topla voda'] = (
        item['Topla voda']
        .astype('string')
        .str.strip()
        .str.lower()
        .map({'da': True, 'ne': False})
        .astype('boolean')
    )

    return item

def preprocess(item):
    item = pd.DataFrame([item])
    item = normalize_missing_df(item)

    item = item.replace('Nan', np.nan)
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
    item = clean_topla_voda(item)

    return item.iloc[0].to_dict()