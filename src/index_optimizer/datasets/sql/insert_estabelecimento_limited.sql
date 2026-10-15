INSERT INTO cnpj.estabelecimento (
    cnpj_basico, cnpj_ordem, cnpj_dv, identificador_matriz_filial,
    nome_fantasia, situacao_cadastral, data_situacao_cadastral,
    motivo_situacao_cadastral, nome_cidade_exterior, pais,
    data_inicio_atividade, cnae_fiscal_principal, cnae_fiscal_secundaria,
    tipo_logradouro, logradouro, numero, complemento, bairro, cep, uf,
    municipio, ddd_1, telefone_1, ddd_2, telefone_2, ddd_fax, fax,
    correio_eletronico, situacao_especial, data_situacao_especial
)
SELECT
    NULLIF(trim(s.c0), ''), NULLIF(trim(s.c1), ''), NULLIF(trim(s.c2), ''),
    NULLIF(trim(s.c3), '')::integer, NULLIF(trim(s.c4), ''),
    NULLIF(trim(s.c5), '')::integer, cnpj.parse_date(s.c6),
    NULLIF(trim(s.c7), '')::integer, NULLIF(trim(s.c8), ''), NULLIF(trim(s.c9), '')::integer,
    cnpj.parse_date(s.c10),
    NULLIF(trim(s.c11), '')::integer,
    NULLIF(trim(s.c12), ''), NULLIF(trim(s.c13), ''), NULLIF(trim(s.c14), ''),
    NULLIF(trim(s.c15), ''), NULLIF(trim(s.c16), ''), NULLIF(trim(s.c17), ''),
    NULLIF(trim(s.c18), ''), NULLIF(trim(s.c19), ''), NULLIF(trim(s.c20), '')::integer,
    NULLIF(trim(s.c21), ''), NULLIF(trim(s.c22), ''), NULLIF(trim(s.c23), ''),
    NULLIF(trim(s.c24), ''), NULLIF(trim(s.c25), ''), NULLIF(trim(s.c26), ''),
    NULLIF(trim(s.c27), ''), NULLIF(trim(s.c28), ''), cnpj.parse_date(s.c29)
FROM selected_establishment s
JOIN selected_cnpj selected ON selected.cnpj_basico = NULLIF(trim(s.c0), '')
WHERE EXISTS (
    SELECT 1 FROM cnpj.empresa e WHERE e.cnpj_basico = NULLIF(trim(s.c0), '')
)
ON CONFLICT (cnpj_basico, cnpj_ordem, cnpj_dv) DO NOTHING;
