# Estado do desenvolvimento

## Fase atual

- **Número e nome:** Fase 4 — Seleção e preparação da massa de dados
- **Estado:** Concluída
- **Última atualização:** 2026-10-15

## Fases

| Fase | Estado | Evidência |
|---|---|---|
| 0 — Inspeção | Concluída | Estrutura e decisões registradas no histórico inicial |
| 1 — Requisitos e arquitetura | Concluída | Arquitetura definida no plano do projeto |
| 2 — Estrutura Python | Concluída | CLI, configuração, empacotamento e testes iniciais |
| 3 — PostgreSQL Docker | Concluída | `compose.yaml`, healthcheck e porta local restrita |
| 4 — Massa de dados | Concluída | 1.000.000 empresas e 1.000.000 estabelecimentos carregados; socio não carregada |
| 5 — Conexão e catálogo | Pendente | — |
| 6 — Validação SQL e EXPLAIN | Pendente | — |
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

## Próxima atualização

A próxima fase será a inspeção do catálogo PostgreSQL.
