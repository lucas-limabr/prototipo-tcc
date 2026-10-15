INSERT INTO cnpj.empresa (
    cnpj_basico,
    razao_social,
    natureza_juridica,
    qualificacao_responsavel,
    capital_social,
    porte,
    ente_federativo
)
SELECT DISTINCT ON (s.c0)
    NULLIF(trim(s.c0), ''),
    NULLIF(trim(s.c1), ''),
    NULLIF(trim(s.c2), '')::integer,
    NULLIF(trim(s.c3), '')::integer,
    replace(NULLIF(trim(s.c4), ''), ',', '.')::numeric(18, 2),
    NULLIF(trim(s.c5), '')::integer,
    NULLIF(trim(s.c6), '')
FROM stg_empresa s
JOIN selected_cnpj selected ON selected.cnpj_basico = NULLIF(trim(s.c0), '')
ORDER BY s.c0, s.c1 NULLS LAST
ON CONFLICT (cnpj_basico) DO NOTHING;
