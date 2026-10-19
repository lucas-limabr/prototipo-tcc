# Metodologia do experimento final

## Objetivo

Avaliar, em um PostgreSQL de laboratório, se a recomendação e aplicação
controlada de um índice B-tree simples altera o plano e reduz o tempo de
execução de consultas representativas do protótipo. O experimento não pretende
provar causalidade ou significância estatística.

## Ambiente e dados

- Execução registrada em 2026-10-15, no banco Docker `index_lab`.
- PostgreSQL 17.11, host local, uma conexão por vez e sem carga concorrente
  conhecida.
- Meta de carga: 5.000.000 de linhas em `cnpj.empresa` e 5.000.000 em
  `cnpj.estabelecimento`. A quantidade efetiva depende das partições disponíveis
  no manifesto e deve ser confirmada pela validação.
- A tabela `cnpj.estabelecimento` é a tabela principal; os arquivos brutos e
  credenciais permanecem fora do Git.
- Índices de integridade e índices preexistentes foram preservados. O índice
  experimental recebeu nome determinístico:
  `ixo_estabelecimento_uf_idx_f71e437d`.

## Consultas previamente definidas

### Q01 — filtro seletivo

```sql
SELECT e.cnpj_basico
FROM cnpj.estabelecimento AS e
WHERE e.uf = 'SP'
```

Avalia filtro em coluna sem índice equivalente antes da intervenção.

### Q02 — junção

```sql
SELECT e.cnpj_basico, p.porte
FROM cnpj.estabelecimento AS e
JOIN cnpj.empresa AS p ON p.cnpj_basico = e.cnpj_basico
WHERE e.uf = 'SP'
```

Avalia junção e filtro, registrando quando as chaves já estão cobertas por
índices de integridade ou pelo índice aplicado em Q01.

### Q03 — ordenação

```sql
SELECT e.cnpj_basico, e.data_inicio_atividade
FROM cnpj.estabelecimento AS e
ORDER BY e.data_inicio_atividade DESC NULLS LAST
LIMIT 1000
```

Avalia uma ordenação isolada. A heurística deve permanecer inconclusiva quando
não houver evidência suficiente para recomendar um índice.

## Protocolo executado

1. Inspecionar o catálogo permitido (`cnpj`) e obter o plano estimado.
2. Validar a consulta como leitura antes de cada operação.
3. Executar dois aquecimentos separados e cinco medições válidas para Q01.
4. Extrair oportunidades, gerar o *dry run* e revisar o DDL.
5. Aplicar explicitamente somente o índice recomendado no laboratório.
6. Repetir o plano e as cinco medições de Q01.
7. Comparar medianas, quantidade de linhas, plano e índice criado.
8. Executar três medições, após a intervenção, para Q02 e Q03 apenas como
   observação complementar; elas não são comparações causais pré/pós.

O resultado agregado está em
[fase15-filtro-uf.json](experimentos/fase15-filtro-uf.json). O protocolo usa
`EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` e não transfere os resultados das
consultas para a aplicação.

## Resultados

| Consulta | Plano | Mediana (ms) | Oportunidade/recomendação |
|---|---|---:|---|
| Q01 antes | `Seq Scan` | 854,946 | `uf`: recomendado |
| Q01 depois | `Bitmap Heap Scan` | 802,909 | índice criado; redução de 6,09% e speedup de 1,065x |
| Q02 após Q01 | `Hash Join` | 4.351,088 | chaves equivalentes existentes; `uf` já existente |
| Q03 após Q01 | `Limit` | 1.039,927 | ordenação: indeterminada, sem aplicação |

Q01 observou a mesma quantidade de linhas antes e depois, e o plano mudou.
O ganho ultrapassou o limiar operacional de 5%, mas a amostra é única e não
permite generalização.

## Desvios e limitações

- O plano inicial previa comparar várias consultas com aplicação independente;
  nesta execução somente Q01 teve ciclo completo pré/pós para evitar acumular
  índices experimentais entre tratamentos.
- Q02 e Q03 foram observadas após Q01, portanto seus tempos não são uma linha de
  base causal.
- Cinco repetições são suficientes para o protótipo, mas não substituem um
  desenho estatístico com mais sessões e controle de cache.
- O PostgreSQL pode escolher corretamente uma varredura sequencial; uma
  `Seq Scan` isolada não é evidência de problema.
- A heurística suporta apenas B-tree simples e não considera seletividade,
  frequência real de consultas, custo de manutenção, concorrência ou índices
  compostos.
- Cache, autovacuum, estatísticas e estado do contêiner podem influenciar os
  tempos.
- A massa usa uma seleção limitada da referência mensal e não representa o
  universo nacional completo.
