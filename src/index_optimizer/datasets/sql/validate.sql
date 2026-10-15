SELECT 'empresa >= 1' AS check_name,
       count(*)::text AS value,
       count(*) > 0 AS ok
FROM cnpj.empresa
UNION ALL
SELECT 'estabelecimento >= 500000',
       count(*)::text,
       count(*) >= 500000
FROM cnpj.estabelecimento
UNION ALL
SELECT 'estabelecimento sem empresa',
       count(*)::text,
       count(*) = 0
FROM cnpj.estabelecimento e
LEFT JOIN cnpj.empresa p USING (cnpj_basico)
WHERE p.cnpj_basico IS NULL
UNION ALL
SELECT 'socio sem empresa',
       count(*)::text,
       count(*) = 0
FROM cnpj.socio s
LEFT JOIN cnpj.empresa p USING (cnpj_basico)
WHERE p.cnpj_basico IS NULL;
