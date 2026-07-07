{{ config(materialized = 'view')}}

/*
    Pisem komentare kako bih stekao tu naviku iako je dosadno,

    SILVER: deterministic 1:1 cleaning of raw halo_oglasi rows.
    Ports: normalize_missing_df, clean_title, clean_price_total,
    clean_price_per_m2, clean_tip_nekretnine, clean_kvadratura,
    clean_br_soba, clean_tip_objekta, clean_stanje_obj, clean_grejanje,
    clean_sprat, clean_uk_sprat, clean_opis, clean_datum_objave,
    plus the raw da/ne -> boolean mapping for all amenity flags.
 
    Text inference from the description and lokacija matching live in GOLD.
 
    NOTE ON COLUMN NAMES: written for snake_case source columns
    (dodatni_opis, broj_soba, ...). If your Bronze table kept the pandas
    names, quote them instead, e.g.  "Dodatni opis"  ->  dodatni_opis.
*/

with source as (
    SELECT *
    FROM {{ ref('int_oglasi_unioned') }}
    WHERE oglas_id IS NOT NULL
),
 -- Pretvaramo sve vrednosti koje treba da budu Nan u pravi NUll
nullified as(
    SELECT oglas_id,
    {{ normalize_missing('title')}} as title,
    {{normalize_missing('price_total')}} as price_total,
    {{normalize_missing('price_per_m2')}} as price_per_m2,
    {{normalize_missing('tip_nekretnine')}} as tip_nekretnine,
    {{normalize_missing('kvadratura')}} as kvadratura,
    {{ normalize_missing('broj_soba') }}         as broj_soba,
    {{ normalize_missing('tip_objekta') }}       as tip_objekta,
    {{ normalize_missing('stanje_objekta') }}    as stanje_objekta,
    {{ normalize_missing('grejanje') }}          as grejanje,
    {{ normalize_missing('sprat') }}             as sprat,
    {{ normalize_missing('ukupna_spratnost') }}  as ukupna_spratnost,
    {{ normalize_missing('dodatni_opis') }}      as dodatni_opis,
    {{ normalize_missing('datum_objave') }}      as datum_objave,
    {{ normalize_missing('uknjizen') }}          as uknjizen,
    {{ normalize_missing('terasa') }}            as terasa,
    {{ normalize_missing('interfon') }}          as interfon,
    {{ normalize_missing('klima') }}             as klima,
    {{ normalize_missing('video_nadzor') }}      as video_nadzor,
    {{ normalize_missing('internet') }}          as internet,
    {{ normalize_missing('parking') }}           as parking,
    {{ normalize_missing('garaza') }}            as garaza,
    {{ normalize_missing('lift') }}              as lift,
    {{ normalize_missing('podrum') }}            as podrum,
    {{ normalize_missing('url') }}           as url,
    {{ normalize_missing('oglasivac') }}     as oglasivac,
    {{ normalize_missing('lokacija_raw') }}  as lokacija_raw,
    izvor,
    created_at
    from source
),

-- sredjujem stringove sprat i preslikavam ih u numericke vrednosti

staged as (
    SELECT *,
    trim(
        regexp_replace(
            replace(
                case lower(trim(sprat))
                    when 'visoko prizemlje' then '0.5'
                    when 'prizemlje' then '0'
                    when 'suteren' then '-0.5'
                    when 'suturen' then '-0.5'
                    when 'vpr' then '0.5'
                    when 'pr' then '0'
                    when 'p' then '0'
                    else lower(trim(sprat))
                end,
            ',','.'),
        '\ysprat\y','','g')
    ) as sprat_s1,

    -- sredjujem ovde grejanje 
    trim(
        regexp_replace(
            regexp_replace(
            regexp_replace(
            regexp_replace(
            regexp_replace(
            regexp_replace(grejanje,
                'Grejanje:\s*', ''),
                '\yKlima uređaj\y|\yKlima uredjaj\y', 'Klima', 'g'),
                '\yOstalo\y', '', 'g'),
                '\s*,\s*', ', ', 'g'),
                '^,\s*|\s*,$', '', 'g'),
                '\s+', ' ', 'g')
        ) as grejanje_s1,

    -- sredjujem ovde datum objave
     regexp_replace(
            trim(
                regexp_replace(
                    (regexp_split_to_array(
                        regexp_replace(
                            regexp_replace(datum_objave, '^\[|\]$', '', 'g'),
                            '''', '', 'g'),
                        '\s+u\s+'))[1],
                    '^Objavljen:\s*', '')
            ),
            '\.$', ''
        ) as datum_s1
    FROM nullified
),

cleaned as(
    SELECT 
        izvor,
        oglasivac,
        oglas_id,
        lokacija_raw,
        url,
        -- sredim title 
        trim(both ',' from
        trim(
            regexp_replace(
                regexp_replace(title, '\d+|EUR|€/m²|€|m²|m2|\.', '', 'g'),
                ', ,', '', 'g')
            )
        )as title,

        -- sredi price_total
        {{parse_price_range('price_total')}} as price_total,
        {{parse_price_range('price_per_m2')}} as price_per_m2,

        -- sredjujem tip nekretnine
        case
            when lower(tip_nekretnine) like '%stan%' then 'stan'
            when lower(tip_nekretnine) ~ 'kuca|kuća'  then 'kuća'
            else null
        end as tip_nekretnine,

        -- sredjume kvadraturu
        nullif(
            substring(replace(lower(kvadratura),',','.') from '[0-9]+\.?[0-9]*'),
            ''
        )::numeric as kvadratura,

        -- broj soba
        nullif(
            substring(replace(lower(broj_soba),',','.') from '[0-9]+\.?[0-9]*'),
            ''
        )::numeric as broj_soba,


        -- tip objekta
        case 
            when tip_objekta is null
                and stanje_objekta in ('Kompletna rekonstrukcija','Renovirano')
                then 'Stara_gradnja'
            when tip_objekta is null and stanje_objekta in ('Novo','Lux')
                then 'Novo_gradnja'
            when tip_objekta = 'Stara gradnje' then 'Stara_gradnja'
            when tip_objekta = 'Novogradnja' then 'Novo_gradnja'
            else tip_objekta
        end as tip_objekta,
        -- clean_stanje_obj
        replace(stanje_objekta, 'Izvorno stanje', 'Izvorno_stanje') as stanje_objekta,

    -- clean_grejanje stage 2: map long labels to canonical tokens
        nullif(
            regexp_replace(
                regexp_replace(
                regexp_replace(
                regexp_replace(
                regexp_replace(
                regexp_replace(
                regexp_replace(
                regexp_replace(grejanje_s1,
                    '\yCentralno grejanje\y', 'centralno', 'g'),
                    '\yPodno grejanje\y', 'podno', 'g'),
                    '\yToplotna pumpa\y', 'toplotna_pumpa', 'g'),
                    '\yEtažno grejanje na struju\y', 'etazno_struja', 'g'),
                    '\yEtažno grejanje na gas\y', 'etazno_gas', 'g'),
                    '\yEtažno grejanje na čvrsto gorivo\y|\yEtažno grejanje na cvrsto gorivo\y', 'etazno_cvrsto_gorivo', 'g'),
                    '\yKlima\y', 'klima', 'g'),
                ',\s*$', ''),
            ''
        ) as grejanje,

        -- clean_sprat stage 2: roman numerals -> arabic, else first number
        case
            when sprat_s1 ~ '^[ivx]+$' then
                case sprat_s1
                    when 'i' then 1 when 'ii' then 2 when 'iii' then 3
                    when 'iv' then 4 when 'v' then 5 when 'vi' then 6
                    when 'vii' then 7 when 'viii' then 8 when 'ix' then 9
                    when 'x' then 10 when 'xi' then 11 when 'xii' then 12
                    when 'xiii' then 13 when 'xiv' then 14 when 'xv' then 15
                    else null
                end
            else
                nullif(
                    substring(sprat_s1 from '-?[0-9]+\.?[0-9]*'),
                    ''
                )::numeric
        end as sprat,


    -- clean_uk_sprat: first integer
    nullif(substring(ukupna_spratnost from '[0-9]+'), '')::int as ukupna_spratnost,

    -- clean_opis: scrub links, percents, phone numbers, e-mails,
    -- agency boilerplate; collapse whitespace, fix punctuation spacing
    nullif(trim(
        regexp_replace(
        regexp_replace(
        regexp_replace(
        regexp_replace(
        regexp_replace(
        regexp_replace(
        regexp_replace(
        regexp_replace(
        regexp_replace(
        regexp_replace(
        regexp_replace(
        regexp_replace(dodatni_opis,
            'http\S+|www\.\S+', '', 'g'),
            '\y\d+([.,]\d+)?\s*%', '', 'g'),
            '(tel(efon)?i?\s*:?\s*)?(\+381|0)\s*\d[0-9[:space:]/()•-]*\d', '', 'g'),
            'Više informacija na:\s*', '', 'g'),
            'Agencijska provizija\.?\s*', '', 'g'),
            'Telefoni?:\s*', '', 'g'),
            'Kontakt van radnog vremena:\s*', '', 'g'),
            '\y[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\y', '', 'g'),
            'Agencijski\s*ID\s*:\s*\d+\s*,?\s*', '', 'g'),
            'Oglas\s*ID\s*:\s*\d+\s*,?\s*', '', 'g'),
            '\s+', ' ', 'g'),
            '\s+([,.:;])', '\1', 'g')
    ), '') as dodatni_opis,


    -- clean_datum_objave stage 2: safe cast, garbage -> NULL
        case
            when datum_s1 ~ '^\d{1,2}\.\d{1,2}\.\d{4}$'
                then to_date(datum_s1, 'DD.MM.YYYY')
            else null
        end as datum_objave,
 
        -- da/ne -> boolean for every amenity flag (unknown stays NULL;
        -- Gold fills the NULLs from the description text)
        case lower(trim(uknjizen))     when 'da' then true when 'ne' then false end as uknjizen,
        case lower(trim(terasa))       when 'da' then true when 'ne' then false end as terasa,
        case lower(trim(interfon))     when 'da' then true when 'ne' then false end as interfon,
        case lower(trim(klima))        when 'da' then true when 'ne' then false end as klima,
        case lower(trim(video_nadzor)) when 'da' then true when 'ne' then false end as video_nadzor,
        case lower(trim(internet))     when 'da' then true when 'ne' then false end as internet,
        case lower(trim(parking))      when 'da' then true when 'ne' then false end as parking,
        case lower(trim(garaza))       when 'da' then true when 'ne' then false end as garaza,
        case lower(trim(lift))         when 'da' then true when 'ne' then false end as lift,
        case lower(trim(podrum))       when 'da' then true when 'ne' then false end as podrum,
 
        created_at
 
    from staged
 
)
 
select * from cleaned
