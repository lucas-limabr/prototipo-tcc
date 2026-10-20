# Execução 4 — Filtro por logradouro

Execução realizada na branch `execucao4-laboratorio` com a consulta solicitada
e a carga CNPJ disponível no PostgreSQL de laboratório.

## Consulta utilizada

```sql
SELECT e.logradouro
FROM cnpj.estabelecimento AS e
WHERE e.logradouro = 'Avenida Rio Branco';
```

## Ambiente

- Branch: `execucao4-laboratorio`
- Banco: `index_lab`
- Schema: `cnpj`
- Empresas: `4.659.598`
- Estabelecimentos: `4.753.435`
- Aquecimentos: `2`
- Medições válidas: `5`

## Comandos executados

```bash
cd /home/lucaslima/Documentos/IF/BSI/TCC2/Prototipo
git branch --show-current
git status --short
find reports -maxdepth 2 -type f -print | sort
set -a
source .env
set +a
export IXO_ALLOWED_SCHEMAS=cnpj
docker compose ps
```

Limpeza dos índices experimentais e dos artefatos anteriores:

```bash
.venv/bin/index-optimizer cleanup \
  --experimental-indexes

rm -f reports/execucao1-*.json \
  reports/execucao2-*.json \
  reports/execucao3-*.json \
  reports/execucao4-*.json \
  reports/charts/*.png

mkdir -p reports/charts
```

O índice experimental da execução anterior,
`ixo_estabelecimento_identificador_matriz_filial_idx_067a9345`, foi removido
antes do baseline.

Execução da análise, baseline, recomendação, aplicação e pós-medição:

```bash
QUERY="SELECT e.logradouro
       FROM cnpj.estabelecimento AS e
       WHERE e.logradouro = 'Avenida Rio Branco'"

set -e

.venv/bin/index-optimizer analyze \
  --query "$QUERY" \
  > reports/execucao4-analyze.json

.venv/bin/index-optimizer benchmark \
  --query "$QUERY" \
  --runs 5 \
  --warmup 2 \
  > reports/execucao4-baseline.json

.venv/bin/index-optimizer optimize \
  --query "$QUERY" \
  --dry-run \
  > reports/execucao4-optimize-dry-run.json

.venv/bin/index-optimizer optimize \
  --query "$QUERY" \
  --apply-indexes \
  > reports/execucao4-optimize-apply.json

.venv/bin/index-optimizer benchmark \
  --query "$QUERY" \
  --runs 5 \
  --warmup 2 \
  > reports/execucao4-after.json
```

Consolidação do relatório pré/pós:

```bash
.venv/bin/python - <<'PY'
import json
from dataclasses import replace
from pathlib import Path
from index_optimizer.database.charts import _benchmark_from_payload
from index_optimizer.database.comparison import compare_benchmarks
from index_optimizer.database.reporting import build_report, report_to_json

baseline_payload = json.loads(Path("reports/execucao4-baseline.json").read_text())
after_payload = json.loads(Path("reports/execucao4-after.json").read_text())
baseline = _benchmark_from_payload(
    baseline_payload["baseline"], baseline_payload["query"]
)
after = _benchmark_from_payload(
    after_payload["baseline"], after_payload["query"]
)
comparison = compare_benchmarks(baseline, after)
comparison = replace(
    comparison,
    created_indexes=("ixo_estabelecimento_logradouro_idx_c2128043",),
    limitations=(
        *comparison.limitations,
        "Execução realizada no PostgreSQL local com a carga CNPJ disponível.",
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
Path("reports/execucao4-report.json").write_text(
    report_to_json(report), encoding="utf-8"
)
print(comparison.explanation)
print("status=", comparison.status.value)
PY
```

Geração dos gráficos:

```bash
.venv/bin/index-optimizer plot \
  --report reports/execucao4-report.json \
  --output-dir reports/charts \
  | tee reports/execucao4-plot.json
```

## Resultados

| Métrica | Antes | Depois |
|---|---:|---:|
| Mediana | 269,091 ms | 0,076 ms |
| Média | 280,491 ms | 0,077 ms |
| Desvio padrão | 28,895 ms | 0,003 ms |

- Status: `MELHORIA`
- Redução da mediana: `99,97%`
- Speedup: `3540,671x`
- Índice aplicado: `ixo_estabelecimento_logradouro_idx_c2128043`

O índice B-tree em `logradouro` mudou substancialmente o custo desta consulta,
que deixou de percorrer a tabela sem índice e passou a localizar os registros
pelo valor filtrado. Os resultados devem ser interpretados dentro das
condições deste laboratório e desta consulta específica.

## Artefatos gerados

- Relatório consolidado:
  `reports/execucao4-report.json`
- Gráfico de medianas:
  `reports/charts/e9ea79ee419d6d47-performance.png`
- Gráfico de médias e desvio padrão:
  `reports/charts/e9ea79ee419d6d47-variability.png`
- Saída do comando de gráficos:
  `reports/execucao4-plot.json`
