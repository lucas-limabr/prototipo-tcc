# Estado do desenvolvimento

## Fase atual

- **Número e nome:** Fase 14 — Testes de integração e fluxo completo
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
| 5 — Conexão e catálogo | Concluída | Catálogo lê schemas, tabelas, colunas, constraints e índices permitidos |
| 6 — Validação SQL e EXPLAIN | Concluída | `database/query_validation.py`, `database/explain.py` e testes unitários |
| 7 — Parser do plano | Concluída | `database/plan_parser.py` e testes unitários |
| 8 — Extração de candidatos | Concluída | `database/opportunities.py` e testes unitários |
| 9 — Motor de recomendação | Concluída | `database/recommendations.py` e testes unitários |
| 10 — Medição pré-indexação | Concluída | `database/benchmark.py` e testes unitários |
| 11 — Aplicação controlada de índices | Concluída | `database/index_apply.py` e testes unitários |
| 12 — Medição pós-indexação | Concluída | `database/comparison.py` e testes unitários |
| 13 — Relatórios e rastreabilidade | Concluída | `database/reporting.py` e testes unitários |
| 14 — Testes de integração e fluxo completo | Concluída | `tests/integration/test_full_flow.py` e suíte de integração |
| 15 — Experimentos finais e documentação acadêmica | Pendente | — |

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

A próxima fase será a extração de oportunidades de indexação.

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

## Entregas da Fase 7

- `database/plan_parser.py` transforma o JSON do PostgreSQL em `QueryPlan`,
  `PlanNode`, `RelationRef` e `PlanCondition`, preservando a resposta original.
- O parser percorre nós filhos recursivamente e extrai relação, alias, custos,
  cardinalidade estimada, filtros, condições de índice/junção e chaves de ordenação.
- Campos opcionais permanecem ausentes sem falha; estruturas malformadas são
  rejeitadas explicitamente.
- Fixtures unitárias cobrem `Seq Scan`, `Index Scan`, `Nested Loop` e `Sort`.

## Entregas da Fase 8

- `database/opportunities.py` extrai oportunidades B-tree de uma coluna a partir
  de filtros, condições de junção e chaves de ordenação.
- Cada oportunidade mantém tabela, coluna, evidência textual e justificativa,
  com verificação da coluna no catálogo.
- Índices existentes equivalentes são marcados e não tratados como ausentes;
  a função somente extrai candidatos e não cria nem recomenda índices.
- Regras ambíguas ou sem relação verificável são ignoradas.

## Entregas da Fase 9

- `database/recommendations.py` aplica regras determinísticas e conservadoras
  sobre oportunidades já extraídas, sem executar DDL ou alterar o banco.
- Os estados são explícitos: `RECOMENDADO`, `NAO_RECOMENDADO`,
  `INDETERMINADO` e `JA_EXISTE_EQUIVALENTE`.
- Filtros e condições de junção podem gerar recomendações B-tree simples;
  ordenação isolada permanece indeterminada por não provar benefício.
- Cada resultado contém tabela, coluna, evidência, justificativa e limitações,
  inclusive quando não há recomendações.

## Entregas da Fase 10

- `database/benchmark.py` executa aquecimentos separados das medições,
  repetições configuráveis e somente conta execuções válidas.
- Cada medição usa `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` após nova validação
  da consulta e em transação `READ ONLY`, registrando tempo do servidor, linhas
  observadas, buffers e erros separados dos tempos.
- O resumo inclui média, mediana, mínimo, máximo e desvio padrão em milissegundos.
- A execução exige pelo menos duas medições válidas e não confunde timeout ou
  erro com tempo de desempenho.
- `pytest -q`: 59 passaram, 3 testes de integração foram excluídos pelo padrão;
  Ruff lint e formatação passaram.
- Medição real no laboratório: 2 execuções válidas, 1 aquecimento, consulta
  `SELECT cnpj_basico FROM cnpj.empresa LIMIT 1`, média de 0,079 ms no servidor.

## Entregas da Fase 11

- `database/index_apply.py` gera DDL com composição segura de identificadores,
  nomes determinísticos limitados a 63 caracteres e modo `dry_run`.
- A aplicação exige confirmação explícita, restringe-se ao ambiente de laboratório
  e revalida índices equivalentes imediatamente antes de cada criação.
- Cada índice é aplicado individualmente; após a criação, a tabela recebe
  `ANALYZE`. Falhas são registradas sem declarar o índice como criado e não há
  `DROP INDEX` automático.

## Entregas da Fase 12

- `database/comparison.py` compara medianas do servidor usando exatamente a
  mesma consulta e protocolo da linha de base.
- O relatório calcula redução percentual e speedup, distinguindo melhoria,
  regressão, ausência de mudança relevante e resultado inconclusivo.
- A comparação verifica quantidade de linhas observadas, registra mudança de
  plano quando os planos foram fornecidos e relaciona índices realmente criados.
- O relatório explicita limitações e não afirma causalidade ou significância
  estatística além do desenho experimental.
- `pytest -q`: 65 passaram, 3 testes de integração foram excluídos pelo padrão;
  Ruff lint e formatação passaram.
- Comparação real no laboratório, sem criação de índice: duas medições antes e
  duas depois da mesma consulta; resultado observado `REGRESSAO` de 0,080 ms
  para 0,088 ms (-10,62%). Esse resultado não atribui causalidade a índice.

## Entregas da Fase 13

- `database/reporting.py` gera relatório estruturado em JSON e Markdown, com
  identificador determinístico do experimento, condição experimental, consulta,
  plano, recomendações, medições, comparação, índices aplicados e limitações.
- O relatório explicita quando não há recomendações e distingue o que foi apenas
  recomendado do que foi realmente aplicado.
- Credenciais não são incluídas; o identificador usa somente consulta e condição
  experimental.

## Entregas da Fase 14

- `tests/integration/test_full_flow.py` cobre, com schema temporário e dados
  determinísticos, validação, `EXPLAIN`, parsing, extração de oportunidades,
  recomendação, benchmark, *dry run* e aplicação explícita de índice.
- O fluxo verifica o índice criado no catálogo e remove o schema de fixture ao
  final de cada teste.
- Uma consulta sem filtro não gera oportunidade, recomendação, DDL ou alteração
  estrutural.
- Os testes de integração permanecem separados dos testes unitários e não usam
  a massa pública volumosa.
- `ruff check src tests`, `ruff format --check src tests` e `pytest -q`
  passaram; a execução `pytest -m integration -q` depende das variáveis
  `IXO_DB_*` e do PostgreSQL de laboratório ativo.
