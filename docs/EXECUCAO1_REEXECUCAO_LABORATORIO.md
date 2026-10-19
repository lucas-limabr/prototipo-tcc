# Reexecução 1 — Laboratório

Esta execução foi realizada na branch `execucao1-laboratorio`, repetindo o
experimento do filtro por UF com a carga CNPJ disponível.

## Consulta utilizada

```sql
SELECT e.cnpj_basico
FROM cnpj.estabelecimento AS e
WHERE e.uf = 'SP';
```

## Ambiente

- Branch: `execucao1-laboratorio`
- Banco: `index_lab`
- Schema: `cnpj`
- Empresas: `4.659.598`
- Estabelecimentos: `4.753.435`
- Aquecimentos: `2`
- Medições válidas: `5`

## Comandos executados

### 1. Conferir branch e ambiente

```bash
cd /home/lucaslima/Documentos/IF/BSI/TCC2/Prototipo
git branch --show-current
git status --short
docker compose ps
```

### 2. Remover relatórios e gráficos anteriores

```bash
rm -f reports/execucao1-*.json \
  reports/execucao2-*.json \
  reports/execucao3-*.json \
  reports/charts/*.png
```

### 3. Limpar índices experimentais

```bash
set -a
source .env
set +a
export IXO_ALLOWED_SCHEMAS=cnpj

.venv/bin/index-optimizer cleanup \
  --experimental-indexes
```

O índice experimental remanescente da execução anterior,
`ixo_estabelecimento_identificador_matriz_filial_idx_067a9345`, foi removido
antes da medição baseline.

### 4. Executar análise, baseline, aplicação e pós-medição

```bash
QUERY="SELECT e.cnpj_basico
       FROM cnpj.estabelecimento AS e
       WHERE e.uf = 'SP'"

set -e

.venv/bin/index-optimizer analyze \
  --query "$QUERY" \
  > reports/execucao1-reexec-analyze.json

.venv/bin/index-optimizer benchmark \
  --query "$QUERY" \
  --runs 5 \
  --warmup 2 \
  > reports/execucao1-reexec-baseline.json

.venv/bin/index-optimizer optimize \
  --query "$QUERY" \
  --dry-run \
  > reports/execucao1-reexec-optimize-dry-run.json

.venv/bin/index-optimizer optimize \
  --query "$QUERY" \
  --apply-indexes \
  > reports/execucao1-reexec-optimize-apply.json

.venv/bin/index-optimizer benchmark \
  --query "$QUERY" \
  --runs 5 \
  --warmup 2 \
  > reports/execucao1-reexec-after.json
```

### 5. Consolidar o relatório JSON

```bash
.venv/bin/python - <<'PY'
import json
from dataclasses import replace
from pathlib import Path
from index_optimizer.database.charts import _benchmark_from_payload
from index_optimizer.database.comparison import compare_benchmarks
from index_optimizer.database.reporting import build_report, report_to_json

baseline_payload = json.loads(
    Path("reports/execucao1-reexec-baseline.json").read_text()
)
after_payload = json.loads(
    Path("reports/execucao1-reexec-after.json").read_text()
)
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
        "Reexecução realizada no PostgreSQL local com a carga CNPJ disponível.",
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
Path("reports/execucao1-reexec-report.json").write_text(
    report_to_json(report), encoding="utf-8"
)
print(comparison.explanation)
print("status=", comparison.status.value)
PY
```

### 6. Gerar os gráficos

```bash
.venv/bin/index-optimizer plot \
  --report reports/execucao1-reexec-report.json \
  --output-dir reports/charts \
  | tee reports/execucao1-reexec-plot.json
```

## Resultados

| Métrica | Antes | Depois |
|---|---:|---:|
| Mediana | 4.138,782 ms | 4.127,560 ms |
| Média | 4.138,165 ms | 4.157,452 ms |
| Desvio padrão | 9,022 ms | 71,749 ms |

- Status: `SEM_MUDANCA_RELEVANTE`
- Redução da mediana: `0,27%`
- Speedup: `1,003x`
- Índice aplicado: `ixo_estabelecimento_uf_idx_f71e437d`

O limiar de relevância configurado é 5%. Portanto, a diferença observada foi
classificada como sem mudança relevante. O desvio padrão aumentou no pós-teste,
indicando maior dispersão entre as medições posteriores.

## Artefatos gerados

- Relatório consolidado:
  `reports/execucao1-reexec-report.json`
- Gráfico de medianas:
  `reports/charts/108a864355573eb6-performance.png`
- Gráfico de médias e desvio padrão:
  `reports/charts/108a864355573eb6-variability.png`
- Saída do comando de gráficos:
  `reports/execucao1-reexec-plot.json`
