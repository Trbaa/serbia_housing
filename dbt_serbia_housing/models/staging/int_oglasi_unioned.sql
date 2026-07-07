{{ config(materialized='view') }}

select
    oglas_id, title, price_total, price_per_m2, tip_nekretnine,
    kvadratura, broj_soba, tip_objekta, stanje_objekta, grejanje,
    sprat, ukupna_spratnost, dodatni_opis, datum_objave,
    uknjizen, terasa, interfon, klima, video_nadzor, internet,
    parking, garaza, lift, podrum,
    url, oglasivac, lokacija as lokacija_raw,
    created_at,
    'halo_oglasi' as izvor
from {{ source('raw', 'halo_oglasi') }}

union all

select
    oglas_id, title, price_total, price_per_m2, tip_nekretnine,
    kvadratura, broj_soba, tip_objekta, stanje_objekta, grejanje,
    sprat, ukupna_spratnost, dodatni_opis, datum_objave,
    uknjizen, terasa, interfon, klima, video_nadzor, internet,
    parking, garaza, lift, podrum,
    url, oglasivac, lokacija as lokacija_raw,
    created_at,
    'nekretnine_rs' as izvor
from {{ source('raw', 'nekretnine_rs') }}

union all

select
    oglas_id, title, price_total, price_per_m2, tip_nekretnine,
    kvadratura, broj_soba, tip_objekta, stanje_objekta, grejanje,
    sprat, ukupna_spratnost, dodatni_opis, datum_objave,
    uknjizen, terasa, interfon, klima, video_nadzor, internet,
    parking, garaza, lift, podrum,
    url, oglasivac, lokacija as lokacija_raw,
    created_at,
    'z4ida' as izvor
from {{ source('raw', 'z4ida') }}