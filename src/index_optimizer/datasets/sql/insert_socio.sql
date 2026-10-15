INSERT INTO cnpj.socio (
    cnpj_basico, identificador_socio, nome_socio, cnpj_cpf_socio,
    qualificacao_socio, data_entrada_sociedade, pais, representante_legal,
    nome_representante, qualificacao_representante, faixa_etaria
)
SELECT
    NULLIF(trim(c0), ''),
    NULLIF(trim(c1), '')::integer,
    NULLIF(trim(c2), ''),
    NULLIF(trim(c3), ''),
    NULLIF(trim(c4), '')::integer,
    to_date(NULLIF(trim(c5), ''), 'DDMMYYYY'),
    NULLIF(trim(c6), '')::integer,
    NULLIF(trim(c7), ''),
    NULLIF(trim(c8), ''),
    NULLIF(trim(c9), '')::integer,
    NULLIF(trim(c10), '')::integer
FROM stg_socio
WHERE NULLIF(trim(c0), '') IS NOT NULL
  AND NULLIF(trim(c3), '') IS NOT NULL
  AND EXISTS (
      SELECT 1 FROM cnpj.empresa e
      WHERE e.cnpj_basico = NULLIF(trim(stg_socio.c0), '')
  )
ON CONFLICT (cnpj_basico, identificador_socio, cnpj_cpf_socio) DO UPDATE SET
    nome_socio = EXCLUDED.nome_socio,
    qualificacao_socio = EXCLUDED.qualificacao_socio,
    data_entrada_sociedade = EXCLUDED.data_entrada_sociedade;
