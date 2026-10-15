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
    NULLIF(trim(c0), ''), NULLIF(trim(c1), ''), NULLIF(trim(c2), ''),
    NULLIF(trim(c3), '')::integer, NULLIF(trim(c4), ''),
    NULLIF(trim(c5), '')::integer, cnpj.parse_date(c6),
    NULLIF(trim(c7), '')::integer, NULLIF(trim(c8), ''), NULLIF(trim(c9), '')::integer,
    cnpj.parse_date(c10),
    NULLIF(trim(c11), '')::integer,
    NULLIF(trim(c12), ''), NULLIF(trim(c13), ''), NULLIF(trim(c14), ''),
    NULLIF(trim(c15), ''), NULLIF(trim(c16), ''), NULLIF(trim(c17), ''),
    NULLIF(trim(c18), ''), NULLIF(trim(c19), ''), NULLIF(trim(c20), '')::integer,
    NULLIF(trim(c21), ''), NULLIF(trim(c22), ''), NULLIF(trim(c23), ''),
    NULLIF(trim(c24), ''), NULLIF(trim(c25), ''), NULLIF(trim(c26), ''),
    NULLIF(trim(c27), ''), NULLIF(trim(c28), ''), cnpj.parse_date(c29)
FROM stg_estabelecimento
WHERE NULLIF(trim(c0), '') IS NOT NULL
  AND EXISTS (
      SELECT 1 FROM cnpj.empresa e
      WHERE e.cnpj_basico = NULLIF(trim(stg_estabelecimento.c0), '')
  )
ON CONFLICT (cnpj_basico, cnpj_ordem, cnpj_dv) DO UPDATE SET
    nome_fantasia = EXCLUDED.nome_fantasia,
    situacao_cadastral = EXCLUDED.situacao_cadastral,
    municipio = EXCLUDED.municipio,
    cnae_fiscal_principal = EXCLUDED.cnae_fiscal_principal;
