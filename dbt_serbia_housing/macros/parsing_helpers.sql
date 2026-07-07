-- {#
--   Port of _parse_range_or_single():
--     "78 000 - 90 000 EUR"  ->  84000   (average of range ends)
--     "120.000 €"            ->  120000  (single value averages to itself)
--   Steps mirror the Python: take first line, split on '-',
--   strip every non-digit from each part, average, round.
-- #}
{% macro parse_price_range(column_name) %}
    case
        when {{ column_name }} is null then null
        else (
            select round(avg(nullif(regexp_replace(part, '[^0-9]', '', 'g'), '')::numeric))
            from unnest(
                regexp_split_to_array(split_part(lower({{ column_name }}), E'\n', 1), '-')
            ) as part
            where regexp_replace(part, '[^0-9]', '', 'g') <> ''
        )::bigint
    end
{% endmacro %}


-- {#
--   Port of the clean_klima / clean_parking / clean_lift / ... family.
--   Priority order replicates the pandas .loc sequence exactly:
--     1. explicit da/ne value from the listing form wins
--     2. negative phrase in description -> false
--        (this also covers pos AND neg together -> false, same as pandas)
--     3. positive phrase in description -> true
--     4. otherwise NULL (unknown)
--   `opis_expr` must be an already-lowercased text expression.
-- #}
{% macro infer_bool(base_col, opis_expr, pos_pattern, neg_pattern) %}
    case
        when {{ base_col }} is not null then {{ base_col }}
        when {{ opis_expr }} ~ '{{ neg_pattern }}' then false
        when {{ opis_expr }} ~ '{{ pos_pattern }}' then true
        else null
    end
{% endmacro %}