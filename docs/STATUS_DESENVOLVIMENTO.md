# Estado do desenvolvimento

## Fase atual

- **Número e nome:** Fase 6 — Validação SQL e EXPLAIN
- **Estado:** Concluída
- **Última atualização:** 2026-10-16

## Fases

| Fase | Estado | Evidência |
|---|---|---|
| 0 — Inspeção | Concluída | Estrutura e decisões registradas no histórico inicial |
| 1 — Requisitos e arquitetura | Concluída | Arquitetura definida no plano do projeto |
| 2 — Estrutura Python | Concluída | CLI, configuração, empacotamento e testes iniciais |
| 3 — PostgreSQL Docker | Concluída | `compose.yaml`, healthcheck e porta local restrita |
| 4 — Massa de dados | Concluída | 1.000.000 empresas e 1.000.000 estabelecimentos carregados; socio não carregada |
| 5 — Conexão e catálogo | Concluída | Catálogo lê schemas, tabelas, colunas, constraints e índices permitidos |
| 6 — Validação SQL e EXPLAIN | Concluída | `database/query_validation.py`, `database/explain.py` e testes unitários |
| 7 — Parser do plano | Pendente | — |
| 8 — Extração de candidatos | Pendente | — |
| 9 — Motor de recomendação | Pendente | — |
| 10–15 — Benchmark e integração | Pendente | — |

## Entregas da Fase 4

- `docs/DADOS_BENCHMARK.md` documenta a fonte oficial do CNPJ e o procedimento.
- `src/index_optimizer/datasets/cnpj.py` baixa arquivos com retomada, manifesto e
  SHA-256, e carrega uma referência no schema `cnpj`.
- `src/index_optimizer/datasets/sql/` contém schema, inserções e validação.
- `/home/lucaslima/Compartilhada/DadosTCC2` armazena os arquivos e o volume
  PostgreSQL, fora do Git.

## Validações executadas

- `pytest -q`: 27 passaram, 1 teste de integração foi excluído pelo padrão.
- `ruff check .`: passou.
- `ruff format --check .`: passou.
- `docker compose config`: passou com variáveis locais.
- A referência remota `2026-10` foi listada; a seleção `--parts 1` tem ~2,26 GiB.
- O download foi concluído em `/home/lucaslima/cnpj-data/2026-10` com manifesto e
  hashes.
- O banco PostgreSQL foi iniciado e o schema CNPJ validado antes do daemon Docker
  ficar indisponível para a continuação da carga.
- Carga limitada concluída no PostgreSQL: `empresa` 1.000.000,
  `estabelecimento` 1.000.000 e `socio` 0.
- Datas são normalizadas para `date`, aceitando `YYYYMMDD` e `DDMMYYYY`;
  valores criticamente inválidos são tratados como ausentes.

## Entregas da Fase 5

- `database/catalog.py` lê schemas, tabelas, colunas, constraints e índices
  somente nos schemas permitidos.
- A inspeção usa parâmetros PostgreSQL (`ANY(%s)`), sem concatenar nomes de
  schemas, e roda em transação `READ ONLY`.
- Testes unitários cobrem transformação dos metadados e escopo vazio.
- Teste de integração cobre o schema `cnpj` do laboratório.
- `pytest -m integration -q`: 2 testes de integração passaram.
- `pytest -q`: 30 testes passaram; 2 testes de integração foram excluídos pelo
  padrão.
- Ruff lint e formatação passaram.

## Próxima atualização

A próxima fase será o parser do plano estimado, sem execução da consulta.

## Entregas da Fase 6

- `database/query_validation.py` aceita somente uma instrução `SELECT`/CTE de
  leitura, rejeitando DML, DDL, `SELECT INTO`, bloqueios de linha, funções
  potencialmente perigosas, SQL inválido e schemas fora do escopo permitido.
- `database/explain.py` captura `EXPLAIN (FORMAT JSON)` sem `ANALYZE`, dentro de
  transação `READ ONLY`, reutilizando os timeouts da conexão e preservando o
  JSON bruto junto do objeto `Plan`.
- Testes unitários cobrem consultas aceitas, entradas proibidas, parser inválido
  e preservação do plano sem execução.
- `pytest -q`: 42 passaram, 3 testes de integração foram excluídos pelo padrão;
  Ruff lint e formatação passaram.
- A senha persistida do usuário `index_lab_user` foi alinhada à configuração do
  `.env` sem recriar o volume; os três testes de integração passaram.
