# Execução 2 — Filtro por data de situação cadastral

Execução realizada na branch `execucao2-laboratorio` com a consulta solicitada
e a carga CNPJ disponível no PostgreSQL de laboratório.

## Consulta utilizada

```sql
SELECT count(e.data_situacao_cadastral) AS contagemEmpresasDecada2010
FROM cnpj.estabelecimento AS e
WHERE e.data_situacao_cadastral BETWEEN DATE '2010-01-01'
  AND DATE '2020-01-01';
```

## Ambiente

- Branch: `execucao2-laboratorio`
- Banco: `index_lab`
- Schema: `cnpj`
- Empresas: `4.659.598`
- Estabelecimentos: `4.753.435`
- Aquecimentos: `2`
- Medições válidas: `5`

## Comandos executados

### 1. Conferir o laboratório

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

### 2. Limpar índices e artefatos anteriores

```bash
.venv/bin/index-optimizer cleanup \
  --experimental-indexes

rm -f reports/execucao1-*.json \
  reports/execucao2-*.json \
  reports/execucao3-*.json \
  reports/charts/*.png

mkdir -p reports/charts
```

O índice experimental da execução anterior,
`ixo_estabelecimento_uf_idx_f71e437d`, foi removido antes do baseline.
O diretório `reports/charts` foi recriado após a limpeza para receber os novos
artefatos.

### 3. Executar análise, baseline, recomendação, aplicação e pós-medição

```bash
QUERY="SELECT count(e.data_situacao_cadastral) AS contagemEmpresasDecada2010
       FROM cnpj.estabelecimento AS e
       WHERE e.data_situacao_cadastral BETWEEN DATE '2010-01-01'
         AND DATE '2020-01-01'"

set -e

.venv/bin/index-optimizer analyze \
  --query "$QUERY" \
  > reports/execucao2-analyze.json

.venv/bin/index-optimizer benchmark \
  --query "$QUERY" \
  --runs 5 \
  --warmup 2 \
  > reports/execucao2-baseline.json

.venv/bin/index-optimizer optimize \
  --query "$QUERY" \
  --dry-run \
  > reports/execucao2-optimize-dry-run.json

.venv/bin/index-optimizer optimize \
  --query "$QUERY" \
  --apply-indexes \
  > reports/execucao2-optimize-apply.json

.venv/bin/index-optimizer benchmark \
  --query "$QUERY" \
  --runs 5 \
  --warmup 2 \
  > reports/execucao2-after.json
```

### 4. Consolidar o relatório pré/pós

```bash
.venv/bin/python - <<'PY'
import json
from dataclasses import replace
from pathlib import Path
from index_optimizer.database.charts import _benchmark_from_payload
from index_optimizer.database.comparison import compare_benchmarks
from index_optimizer.database.reporting import build_report, report_to_json

baseline_payload = json.loads(Path("reports/execucao2-baseline.json").read_text())
after_payload = json.loads(Path("reports/execucao2-after.json").read_text())
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
        "ixo_estabelecimento_data_situacao_cadastral_idx_929b1efb",
    ),
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
Path("reports/execucao2-report.json").write_text(
    report_to_json(report), encoding="utf-8"
)
print(comparison.explanation)
print("status=", comparison.status.value)
PY
```

### 5. Gerar os gráficos

```bash
.venv/bin/index-optimizer plot \
  --report reports/execucao2-report.json \
  --output-dir reports/charts \
  | tee reports/execucao2-plot.json
```

## Resultados

| Métrica | Antes | Depois |
|---|---:|---:|
| Mediana | 1.938,029 ms | 1.820,611 ms |
| Média | 1.944,447 ms | 1.821,496 ms |
| Desvio padrão | 17,653 ms | 15,829 ms |

- Status: `MELHORIA`
- Redução da mediana: `6,06%`
- Speedup: `1,064x`
- Índice aplicado:
  `ixo_estabelecimento_data_situacao_cadastral_idx_929b1efb`

O limiar de relevância configurado é 5%; portanto, a redução observada foi
classificada como melhoria relevante. O desvio padrão também diminuiu
ligeiramente após a indexação.

## Artefatos gerados

- Relatório consolidado:
  `reports/execucao2-report.json`
- Gráfico de medianas:
  `reports/charts/47697cac457a233f-performance.png`
- Gráfico de médias e desvio padrão:
  `reports/charts/47697cac457a233f-variability.png`
- Saída do comando de gráficos:
  `reports/execucao2-plot.json`
