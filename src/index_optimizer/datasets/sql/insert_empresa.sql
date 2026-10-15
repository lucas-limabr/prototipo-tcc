INSERT INTO cnpj.empresa (
    cnpj_basico,
    razao_social,
    natureza_juridica,
    qualificacao_responsavel,
    capital_social,
    porte,
    ente_federativo
)
SELECT DISTINCT ON (c0)
    NULLIF(trim(c0), ''),
    NULLIF(trim(c1), ''),
    NULLIF(trim(c2), '')::integer,
    NULLIF(trim(c3), '')::integer,
    replace(NULLIF(trim(c4), ''), ',', '.')::numeric(18, 2),
    NULLIF(trim(c5), '')::integer,
    NULLIF(trim(c6), '')
FROM stg_empresa
WHERE NULLIF(trim(c0), '') IS NOT NULL
ORDER BY c0, c1 NULLS LAST
ON CONFLICT (cnpj_basico) DO UPDATE SET
    razao_social = EXCLUDED.razao_social,
    natureza_juridica = EXCLUDED.natureza_juridica,
    qualificacao_responsavel = EXCLUDED.qualificacao_responsavel,
    capital_social = EXCLUDED.capital_social,
    porte = EXCLUDED.porte,
    ente_federativo = EXCLUDED.ente_federativo;
