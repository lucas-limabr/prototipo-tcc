CREATE SCHEMA IF NOT EXISTS cnpj;

CREATE OR REPLACE FUNCTION cnpj.parse_date(value text)
RETURNS date
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    normalized text := trim(value);
    year_value integer;
    month_value integer;
    day_value integer;
BEGIN
    IF normalized IS NULL OR normalized = '' OR normalized !~ '^[0-9]{8}$' THEN
        RETURN NULL;
    END IF;

    IF substring(normalized, 1, 4)::integer BETWEEN 1800 AND 2200 THEN
        year_value := substring(normalized, 1, 4)::integer;
        month_value := substring(normalized, 5, 2)::integer;
        day_value := substring(normalized, 7, 2)::integer;
    ELSIF substring(normalized, 5, 4)::integer BETWEEN 1800 AND 2200 THEN
        day_value := substring(normalized, 1, 2)::integer;
        month_value := substring(normalized, 3, 2)::integer;
        year_value := substring(normalized, 5, 4)::integer;
    ELSE
        RETURN NULL;
    END IF;

    IF month_value NOT BETWEEN 1 AND 12
       OR day_value < 1
       OR day_value > (CASE
           WHEN month_value IN (4, 6, 9, 11) THEN 30
           WHEN month_value = 2 AND (
               year_value % 400 = 0
               OR (year_value % 4 = 0 AND year_value % 100 <> 0)
           ) THEN 29
           WHEN month_value = 2 THEN 28
           ELSE 31
       END) THEN
        RETURN NULL;
    END IF;

    RETURN make_date(year_value, month_value, day_value);
END;
$$;

CREATE TABLE IF NOT EXISTS cnpj.empresa (
    cnpj_basico char(8) PRIMARY KEY,
    razao_social text,
    natureza_juridica integer,
    qualificacao_responsavel integer,
    capital_social numeric(18, 2),
    porte integer,
    ente_federativo text
);

CREATE TABLE IF NOT EXISTS cnpj.estabelecimento (
    cnpj_basico char(8) NOT NULL,
    cnpj_ordem char(4) NOT NULL,
    cnpj_dv char(2) NOT NULL,
    identificador_matriz_filial integer,
    nome_fantasia text,
    situacao_cadastral integer,
    data_situacao_cadastral date,
    motivo_situacao_cadastral integer,
    nome_cidade_exterior text,
    pais integer,
    data_inicio_atividade date,
    cnae_fiscal_principal integer,
    cnae_fiscal_secundaria text,
    tipo_logradouro text,
    logradouro text,
    numero text,
    complemento text,
    bairro text,
    cep char(8),
    uf char(2),
    municipio integer,
    ddd_1 text,
    telefone_1 text,
    ddd_2 text,
    telefone_2 text,
    ddd_fax text,
    fax text,
    correio_eletronico text,
    situacao_especial text,
    data_situacao_especial date,
    PRIMARY KEY (cnpj_basico, cnpj_ordem, cnpj_dv),
    FOREIGN KEY (cnpj_basico) REFERENCES cnpj.empresa (cnpj_basico)
);

CREATE TABLE IF NOT EXISTS cnpj.socio (
    cnpj_basico char(8) NOT NULL,
    identificador_socio integer NOT NULL,
    nome_socio text,
    cnpj_cpf_socio text NOT NULL,
    qualificacao_socio integer,
    data_entrada_sociedade date,
    pais integer,
    representante_legal text,
    nome_representante text,
    qualificacao_representante integer,
    faixa_etaria integer,
    PRIMARY KEY (cnpj_basico, identificador_socio, cnpj_cpf_socio),
    FOREIGN KEY (cnpj_basico) REFERENCES cnpj.empresa (cnpj_basico)
);

CREATE TABLE IF NOT EXISTS cnpj.cnae (
    codigo integer PRIMARY KEY,
    descricao text NOT NULL
);

CREATE TABLE IF NOT EXISTS cnpj.motivo_situacao (
    codigo integer PRIMARY KEY,
    descricao text NOT NULL
);

CREATE TABLE IF NOT EXISTS cnpj.municipio (
    codigo integer PRIMARY KEY,
    descricao text NOT NULL
);

CREATE TABLE IF NOT EXISTS cnpj.natureza_juridica (
    codigo integer PRIMARY KEY,
    descricao text NOT NULL
);

CREATE TABLE IF NOT EXISTS cnpj.pais (
    codigo integer PRIMARY KEY,
    descricao text NOT NULL
);

CREATE TABLE IF NOT EXISTS cnpj.qualificacao_socio (
    codigo integer PRIMARY KEY,
    descricao text NOT NULL
);

CREATE TABLE IF NOT EXISTS cnpj.carga (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tabela text NOT NULL,
    referencia text NOT NULL,
    arquivos jsonb NOT NULL,
    linhas bigint NOT NULL CHECK (linhas >= 0),
    carregado_em timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS estabelecimento_cnae_idx
    ON cnpj.estabelecimento (cnae_fiscal_principal);
CREATE INDEX IF NOT EXISTS estabelecimento_municipio_idx
    ON cnpj.estabelecimento (municipio);
CREATE INDEX IF NOT EXISTS socio_cnpj_basico_idx
    ON cnpj.socio (cnpj_basico);
