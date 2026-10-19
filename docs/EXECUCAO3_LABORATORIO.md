# Execução 3 — Filtro por matriz/filial

Execução realizada na branch `execucao3-laboratorio`, usando a carga CNPJ
disponível no PostgreSQL de laboratório.

## Consulta utilizada

```sql
SELECT count(e.identificador_matriz_filial) AS contagemMatriz
FROM cnpj.estabelecimento AS e
WHERE e.identificador_matriz_filial = 1;
```

## Ambiente

- Branch: `execucao3-laboratorio`
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
docker compose ps
```

Limpeza dos relatórios e gráficos anteriores:

```bash
rm -f reports/execucao2-*.json \
  reports/execucao3-*.json \
  reports/charts/*.png
```

Limpeza dos índices experimentais:

```bash
set -a
source .env
set +a
export IXO_ALLOWED_SCHEMAS=cnpj

.venv/bin/index-optimizer cleanup \
  --experimental-indexes
```

O índice da execução anterior foi removido antes do novo baseline:
`ixo_estabelecimento_data_situacao_cadastral_idx_929b1efb`.

Execução da análise, baseline, recomendação, aplicação e medição posterior:

```bash
QUERY="SELECT count(e.identificador_matriz_filial) AS contagemMatriz
       FROM cnpj.estabelecimento AS e
       WHERE e.identificador_matriz_filial = 1"

set -e

.venv/bin/index-optimizer analyze \
  --query "$QUERY" \
  > reports/execucao3-analyze.json

.venv/bin/index-optimizer benchmark \
  --query "$QUERY" \
  --runs 5 \
  --warmup 2 \
  > reports/execucao3-baseline.json

.venv/bin/index-optimizer optimize \
  --query "$QUERY" \
  --dry-run \
  > reports/execucao3-optimize-dry-run.json

.venv/bin/index-optimizer optimize \
  --query "$QUERY" \
  --apply-indexes \
  > reports/execucao3-optimize-apply.json

.venv/bin/index-optimizer benchmark \
  --query "$QUERY" \
  --runs 5 \
  --warmup 2 \
  > reports/execucao3-after.json
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

baseline_payload = json.loads(Path("reports/execucao3-baseline.json").read_text())
after_payload = json.loads(Path("reports/execucao3-after.json").read_text())
baseline = _benchmark_from_payload(
    baseline_payload["baseline"], baseline_payload["query"]
)
after = _benchmark_from_payload(
    after_payload["baseline"], after_payload["query"]
)
comparison = compare_benchmarks(baseline, after)
comparison = replace(
    comparison,
    created_indexes=(
        "ixo_estabelecimento_identificador_matriz_filial_idx_067a9345",
    ),
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
Path("reports/execucao3-report.json").write_text(
    report_to_json(report), encoding="utf-8"
)
print(comparison.explanation)
print("status=", comparison.status.value)
PY
```

Geração dos dois gráficos:

```bash
.venv/bin/index-optimizer plot \
  --report reports/execucao3-report.json \
  --output-dir reports/charts \
  | tee reports/execucao3-plot.json
```

## Resultados

| Métrica | Antes | Depois |
|---|---:|---:|
| Mediana | 4.526,322 ms | 4.434,629 ms |
| Média | 4.515,924 ms | 4.445,057 ms |
| Desvio padrão | 37,916 ms | 46,596 ms |

- Status: `SEM_MUDANCA_RELEVANTE`
- Redução da mediana: `2,03%`
- Speedup: `1,021x`
- Índice aplicado:
  `ixo_estabelecimento_identificador_matriz_filial_idx_067a9345`

O limiar de relevância configurado é 5%; portanto, a redução observada foi
classificada como sem mudança relevante. O desvio padrão aumentou após a
indexação, indicando maior dispersão entre as cinco medições posteriores.

## Artefatos

- Relatório consolidado:
  `reports/execucao3-report.json`
- Gráfico de medianas:
  `reports/charts/478fa45d02909f7a-performance.png`
- Gráfico de médias e desvio padrão:
  `reports/charts/478fa45d02909f7a-variability.png`
- Relatório do comando de gráficos:
  `reports/execucao3-plot.json`
