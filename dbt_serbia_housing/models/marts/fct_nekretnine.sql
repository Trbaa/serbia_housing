{{ config(materialized='table') }}

/*
    GOLD: enrichment on top of Silver.
    Ports: clean_lokacija (seed join, longest match wins, title before opis)
    and the whole pos/neg inference family: clean_uknjizen, clean_terasa,
    clean_interfon, clean_klima, clean_video_nadzor, clean_internet,
    clean_parking, clean_garaza, clean_lift, clean_podrum.

    Materialized as a table on purpose: ~20k rows x 252 location regexes
    is too expensive to re-run on every SELECT as a view.
*/

with silver as (

    select * from {{ ref('stg_oglasi') }}

),

-- Pre-compute the normalized/lowercased text once instead of per-pattern
prepared as (

    select
        *,
        -- _normalize(): lowercase + strip Serbian diacritics
        translate(lower(coalesce(title, '')),        'čćšžđ', 'ccszd') as title_norm,
        translate(lower(coalesce(dodatni_opis, '')), 'čćšžđ', 'ccszd') as opis_norm,
        lower(coalesce(dodatni_opis, ''))                              as opis_l
    from silver

),

-- clean_lokacija: title match takes priority over description match;
-- within each, the LONGEST location name wins (so 'Bezanijska Kosa 2'
-- beats 'Bezanijska Kosa'). '.' is the only regex metachar in the seed,
-- escaped inline. \y = Postgres word boundary (\b in Python).
lokacija_matched as (

    select
        p.*,
        coalesce(t.lokacija, o.lokacija, 'Nepoznato') as lokacija
    from prepared p

    left join lateral (
        select l.lokacija
        from {{ ref('lokacije') }} l
        where p.title_norm ~ ('\y' || replace(l.lokacija_norm, '.', '\.') || '\y')
        order by length(l.lokacija_norm) desc
        limit 1
    ) t on true

    left join lateral (
        select l.lokacija
        from {{ ref('lokacije') }} l
        where p.opis_norm ~ ('\y' || replace(l.lokacija_norm, '.', '\.') || '\y')
        order by length(l.lokacija_norm) desc
        limit 1
    ) o on true

)

select
    izvor || '_' || oglas_id as unified_id,
    oglas_id,
    title,
    lokacija,
    price_total,
    price_per_m2,
    tip_nekretnine,
    kvadratura,
    broj_soba,
    tip_objekta,
    stanje_objekta,
    grejanje,
    sprat,
    ukupna_spratnost,

    -- clean_uknjizen: the only one-sided rule in the Python — it only
    -- ever fills TRUE (pos without neg); it never infers FALSE
    case
        when uknjizen is not null then uknjizen
        when opis_l ~ 'uknjižen\s+na|uknjizen\s+na|uknjižena\s+površina|uknjizena\s+povrsina|uknjiženo\s+\d+|uknjizeno\s+\d+|stan\s+je\s+uknjižen|stan\s+je\s+uknjizen|uknjižen\s+je|uknjizen\s+je|uknjižena\s+je|uknjizena\s+je|\yuknjižen\y|\yuknjizen\y'
             and opis_l !~ 'nije\s+uknjižen|nije\s+uknjizen|biće\s+uknjižen|bice\s+uknjizen|uskoro\s+uknjižen|uskoro\s+uknjizen|u\s+procesu\s+uknjiženja|u\s+procesu\s+uknjizenja|predat[ao]?\s+za\s+uknjiženje|predat[ao]?\s+za\s+uknjizenje|može\s+uknjiženje|moze\s+uknjizenje|zgrada\s+je\s+uknjižena|zgrada\s+je\s+uknjizena|objekat\s+je\s+uknjižen|objekat\s+je\s+uknjizen'
            then true
        else null
    end as uknjizen,

    {{ infer_bool('terasa', 'opis_l',
        '\yterasa\y|\yterase\y|\ylođa\y|\ylođe\y|\ylodja\y|\ylodje\y',
        'bez\s+terase|bez\s+terasa|nema\s+terasu|nema\s+terase|bez\s+lođe|bez\s+lođa|bez\s+lodje|bez\s+lodja'
    ) }} as terasa,

    -- clean_interfon has one extra rule before the pos/neg logic:
    -- new construction defaults to TRUE
    case
        when interfon is not null then interfon
        when tip_objekta = 'Novo_gradnja' then true
        when opis_l ~ 'bez\s+interfona|nema\s+interfon|bez\s+interfonske\s+veze' then false
        when opis_l ~ '\yinterfon\y|\yinterfonsk\w*\y|\yvideo\s+interfon\y' then true
        else null
    end as interfon,

    {{ infer_bool('klima', 'opis_l',
        '\yklima\y|\yklime\y|\yklima uređaj\y|\yklima uredjaj\y|\yklimatizovan\y|\yklimatizirana\y',
        'bez\s+klime|nema\s+klimu|nije\s+ugrađena\s+klima|nije\s+ugradjena\s+klima'
    ) }} as klima,

    {{ infer_bool('video_nadzor', 'opis_l',
        '\yvideo\s*nadzor\y|\yvideo-nadzor\y|\ynadzorne?\s+kamere\y|\ykamere\y|\ykamera\y',
        'bez\s+video\s+nadzora|nema\s+video\s+nadzor|bez\s+nadzornih\s+kamera|nema\s+kamere|bez\s+kamere|bez\s+nadzora'
    ) }} as video_nadzor,

    {{ infer_bool('internet', 'opis_l',
        '\yinternet\y|\ywi[[:space:]-]?fi\y|\yoptički internet\y|\yopticki internet\y|\ykablovski internet\y',
        'bez\s+interneta|nema\s+internet|bez\s+internet priključka|bez\s+internet prikljucka'
    ) }} as internet,

    {{ infer_bool('parking', 'opis_l',
        '\yparking\y',
        'bez\s+parkinga|nema\s+parking|bez\s+parking mesta|bez\s+parkinga\s+i\s+garaže|bez\s+parkinga\s+i\s+garaze'
    ) }} as parking,

    {{ infer_bool('garaza', 'opis_l',
        '\ygaraža\y|\ygaraza\y|\ygaražno\s+mesto\y|\ygarazno\s+mesto\y|\ygaraža\s+u\s+zgradi\y|\ygaraza\s+u\s+zgradi\y',
        'bez\s+garaže|bez\s+garaze|nema\s+garažu|nema\s+garazu|bez\s+garažnog\s+mesta|bez\s+garaznog\s+mesta'
    ) }} as garaza,

    {{ infer_bool('lift', 'opis_l',
        '\ylift\y|\yliftom\y|\ylifta\y',
        'bez\s+lifta|nema\s+lift'
    ) }} as lift,

    {{ infer_bool('podrum', 'opis_l',
        '\ypodrum\y|\ypodrumska\s+prostorija\y|\ypripadajući\s+podrum\y|\ypripadajuci\s+podrum\y',
        'bez\s+podruma|nema\s+podrum|bez\s+pripadajućeg\s+podruma|bez\s+pripadajuceg\s+podruma'
    ) }} as podrum,

    dodatni_opis,
    datum_objave,
    created_at,
    izvor

from lokacija_matched