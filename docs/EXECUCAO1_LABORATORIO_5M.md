# Execução 1 — Laboratório com carga CNPJ ampliada

Este documento registra a execução realizada na branch
`execucao1-laboratorio`, sem alterar a massa de dados, para medir a consulta
antes e depois da aplicação do índice experimental.

## Ambiente e carga

- Branch: `execucao1-laboratorio`
- PostgreSQL: container `index-lab-postgres`
- Banco: `index_lab`
- Schema autorizado na execução: `cnpj`
- Dataset: CNPJ `2026-10`
- Empresas: `4.659.598`
- Estabelecimentos: `4.753.435`
- Consulta:

  ```sql
  SELECT e.cnpj_basico
  FROM cnpj.estabelecimento AS e
  WHERE e.uf = 'SP'
  ```

A carga disponível ficou próxima da meta de 5 milhões porque a segunda
partição de estabelecimentos não estava disponível localmente.

## Comandos executados

Todos os comandos abaixo foram executados a partir da raiz do projeto.

### 1. Conferir branch, estado e relatórios antigos

```bash
cd /home/lucaslima/Documentos/IF/BSI/TCC2/Prototipo
git branch --show-current
git status --short
find reports -maxdepth 2 -type f -print | sort
```

### 2. Remover artefatos anteriores

```bash
rm -f reports/execucao1-after.json \
  reports/execucao1-analyze.json \
  reports/execucao1-baseline.json \
  reports/execucao1-comparison.json \
  reports/execucao1-optimize-apply.json \
  reports/execucao1-optimize-dry-run.json \
  reports/execucao1-report.json \
  reports/execucao1-plot.json \
  reports/charts/b3be7fc82b29cbab-performance.png
```

### 3. Limpar índices experimentais remanescentes

O `IXO_ALLOWED_SCHEMAS` precisa incluir `cnpj`; caso contrário, a limpeza não
enxerga os índices desse schema.

```bash
set -a
source .env
set +a
export IXO_ALLOWED_SCHEMAS=cnpj

.venv/bin/index-optimizer cleanup \
  --experimental-indexes \
  > /tmp/ixo-cleanup-cnpj.json

cat /tmp/ixo-cleanup-cnpj.json
```

Resultado: o índice `ixo_estabelecimento_uf_idx_f71e437d` foi removido antes
do baseline.

### 4. Conferir as contagens

```bash
docker compose exec -T postgres psql \
  -U "$IXO_DB_USER" \
  -d "$IXO_DB_NAME" \
  -c "SELECT 'empresa' AS tabela, count(*) AS registros
      FROM cnpj.empresa
      UNION ALL
      SELECT 'estabelecimento', count(*)
      FROM cnpj.estabelecimento
      ORDER BY tabela;"
```

### 5. Executar análise, baseline, recomendação, aplicação e pós-medição

```bash
QUERY="SELECT e.cnpj_basico
       FROM cnpj.estabelecimento AS e
       WHERE e.uf = 'SP'"

set -e

.venv/bin/index-optimizer analyze \
  --query "$QUERY" \
  > reports/execucao1-analyze.json

.venv/bin/index-optimizer benchmark \
  --query "$QUERY" \
  --runs 5 \
  --warmup 2 \
  > reports/execucao1-baseline.json

.venv/bin/index-optimizer optimize \
  --query "$QUERY" \
  --dry-run \
  > reports/execucao1-optimize-dry-run.json

.venv/bin/index-optimizer optimize \
  --query "$QUERY" \
  --apply-indexes \
  > reports/execucao1-optimize-apply.json

.venv/bin/index-optimizer benchmark \
  --query "$QUERY" \
  --runs 5 \
  --warmup 2 \
  > reports/execucao1-after.json
```

`--warmup 2` executa duas consultas de aquecimento que não entram nas
estatísticas. `--runs 5` coleta cinco medições válidas em cada condição.

### 6. Consolidar o relatório pré/pós em JSON

O comando `benchmark` grava a medição no campo `baseline`. O comando abaixo
carrega esse campo dos dois arquivos, calcula a comparação e gera um relatório
único com `baseline`, `after` e `comparison`.

```bash
.venv/bin/python - <<'PY'
import json
from dataclasses import replace
from pathlib import Path
from index_optimizer.database.charts import _benchmark_from_payload
from index_optimizer.database.comparison import compare_benchmarks
from index_optimizer.database.reporting import build_report, report_to_json

baseline_payload = json.loads(Path("reports/execucao1-baseline.json").read_text())
after_payload = json.loads(Path("reports/execucao1-after.json").read_text())
baseline = _benchmark_from_payload(
    baseline_payload["baseline"], baseline_payload["query"]
)
after = _benchmark_from_payload(
    after_payload["baseline"], after_payload["query"]
)
comparison = compare_benchmarks(baseline, after)
comparison = replace(
    comparison,
    created_indexes=("ixo_estabelecimento_uf_idx_f71e437d",),
    limitations=(
        *comparison.limitations,
        "Experimento executado no PostgreSQL local com a carga CNPJ disponível.",
    ),
)
report = build_report(
    baseline.sql,
    condition={
        "command": "benchmark-comparison",
        "environment": "lab",
        "dataset": "CNPJ 2026-10",
        "empresa_rows": 4659598,
        "estabelecimento_rows": 4753435,
        "runs": 5,
        "warmups": 2,
    },
    baseline=baseline,
    after=after,
    comparison=comparison,
    limitations=comparison.limitations,
)
Path("reports/execucao1-report.json").write_text(
    report_to_json(report), encoding="utf-8"
)
print(comparison.explanation)
print("status=", comparison.status.value)
PY
```

### 7. Gerar os dois gráficos

```bash
.venv/bin/index-optimizer plot \
  --report reports/execucao1-report.json \
  --output-dir reports/charts \
  | tee reports/execucao1-plot.json
```

## Resultados

| Métrica | Antes | Depois |
|---|---:|---:|
| Mediana | 4.570,992 ms | 4.170,594 ms |
| Média | 4.554,521 ms | 4.206,182 ms |
| Desvio padrão | 235,951 ms | 132,516 ms |

A comparação registrou:

- Status: `MELHORIA`
- Redução da mediana: `8,76%`
- Speedup: `1,096x`
- Índice aplicado: `ixo_estabelecimento_uf_idx_f71e437d`

O relatório JSON completo está em
`reports/execucao1-report.json`.

Os gráficos gerados são:

- `reports/charts/108a864355573eb6-performance.png`: medianas antes/depois;
- `reports/charts/108a864355573eb6-variability.png`: médias antes/depois com
  barras de erro de ± desvio padrão.

O segundo gráfico permite verificar se o índice melhorou apenas o tempo típico
ou também tornou as medições mais estáveis. Nesta execução, o desvio padrão
caiu de `235,951 ms` para `132,516 ms`.
