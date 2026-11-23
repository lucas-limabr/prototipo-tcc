QUERY="select e.razao_social
from cnpj.empresa e
where e.porte = 1;"
set -e

.venv/bin/index-optimizer analyze \
  --query "$QUERY" \
  > reports/execucao6-analyze.json

.venv/bin/index-optimizer benchmark \
  --query "$QUERY" \
  --runs 5 \
  --warmup 2 \
  > reports/execucao6-baseline.json

.venv/bin/index-optimizer optimize \
  --query "$QUERY" \
  --dry-run \
  > reports/execucao6-optimize-dry-run.json

.venv/bin/index-optimizer optimize \
  --query "$QUERY" \
  --apply-indexes \
  > reports/execucao6-optimize-apply.json

.venv/bin/index-optimizer benchmark \
  --query "$QUERY" \
  --runs 5 \
  --warmup 2 \
  > reports/execucao6-after.json



.venv/bin/python scripts/consolidate_report.py \
  --baseline reports/execucao6-baseline.json \
  --after reports/execucao6-after.json \
  --output reports/execucao6-report.json

.venv/bin/index-optimizer plot \
  --report reports/execucao6-report.json \
  --output-dir reports/charts \
  | tee reports/execucao6-plot.json


