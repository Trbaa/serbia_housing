{{ config(
    materialized='incremental',
    unique_key='unified_id',
    incremental_strategy='merge'
) }}

SELECT
    oglas_id, url, title, price_total, price_per_m2,
    tip_nekretnine, kvadratura, broj_soba, oglasivac,
    tip_objekta, stanje_objekta, grejanje, sprat,
    ukupna_spratnost, uknjizen, terasa, interfon,
    klima, video_nadzor, internet, parking, garaza,
    lift, podrum, linije_gradskog_prevoza,
    datum_objave, dodatni_opis, lokacija, created_at,
    'z4ida' AS izvor
FROM silver.z4ida
WHERE oglas_id IS NOT NULL
