{%macro normalize_missing(column_name)%}
    nullif(nullif(nullif(nullif(nullif(nullif(
        {{ column_name }},
        ''),' '),'None'), 'Nan'), 'NaN'),'<NA>')
{%endmacro%}