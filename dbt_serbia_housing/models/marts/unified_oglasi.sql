WITH halo AS (
    SELECT * FROM {{ ref('stg_halo_oglasi') }}
),
z4ida AS (
    SELECT * FROM {{ ref('stg_z4ida') }}
),
nekretnine AS (
    SELECT * FROM {{ ref('stg_nekretnine_rs') }}
),
sve_zajedno AS (
    SELECT * FROM halo
    UNION ALL
    SELECT * FROM z4ida
    UNION ALL
    SELECT * FROM nekretnine
)
SELECT
    izvor || '_' || oglas_id AS unified_id,
    izvor,
    oglas_id,
    url,
    title,
    price_total,
    price_per_m2,
    tip_nekretnine,
    kvadratura,
    broj_soba,
    oglasivac,
    tip_objekta,
    stanje_objekta,
    grejanje,
    sprat,
    ukupna_spratnost,
    uknjizen,
    terasa,
    interfon,
    klima,
    video_nadzor,
    internet,
    parking,
    garaza,
    lift,
    podrum,
    linije_gradskog_prevoza,
    datum_objave,
    dodatni_opis,
    lokacija,
    created_at
FROM sve_zajedno