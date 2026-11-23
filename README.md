# index-optimizer

Protótipo de pesquisa do TCC **“Otimização de bancos de bados relacionais: indexação
automatizada para maximização de desempenho**. Analisa consultas `SELECT` no PostgreSQL,
recomenda índices por regras explícitas e, apenas em um banco de laboratório, permite
aplicá-los e comparar o desempenho antes/depois.

Está sendo disponibilizado o link para o [arquivo do Google Colab](https://colab.research.google.com/drive/192kWEeJSX7XeJjQ4W7asqXpaRh0guU8j) referente ao protótipo. Ele reúne, de forma enxuta, todas as explicações, instruções e códigos necessários à execução dos experimentos, abrangendo os procedimentos realizados em cada um deles.

Também está incluído neste repositório o artigo científico de TCC escrito por mim, que será apresentado em minha instituição de ensino, o Instituto Federal de Educação, Ciência e Tecnologia do Sudeste de Minas Gerais - Campus Juiz de Fora. [Artigo científico](article/Artigo_científico_TCC_2_final.pdf)

## Requisitos
- Python ≥ 3.11
- Docker

## Instalação (desenvolvimento)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # ajuste os valores; nunca versione o .env
```

## Uso
```bash
index-optimizer --help
index-optimizer --version
```

## Gráficos de comparação

Para gerar um PNG a partir de um relatório JSON que contenha medições `baseline`,
`after` e `comparison`:

```bash
index-optimizer plot --report reports/experimento.json
```

São salvos por padrão dois arquivos em `reports/charts/`:
`<experiment_id>-performance.png` (medianas) e
`<experiment_id>-variability.png` (médias com barras de erro de ± desvio padrão).
Use `--output-dir PATH` para alterar o diretório. O primeiro gráfico compara o
tempo mediano da query antes/depois; o segundo evidencia a dispersão e a
estabilidade das medições nas duas condições. O rótulo e a cor indicam `MELHORIA`,
`REGRESSAO`, `SEM_MUDANCA_RELEVANTE` ou `INCONCLUSIVO`. Relatórios produzidos
apenas por `analyze`, `benchmark` ou `optimize` não têm automaticamente as duas
etapas necessárias: a aplicação de índices não executa benchmark antes/depois.

## Massa CNPJ

O download e a carga da massa de benchmark são explícitos e mantêm os arquivos
fora do Git. Consulte [docs/DADOS_BENCHMARK.md](docs/DADOS_BENCHMARK.md) para
escolher uma referência mensal, baixar uma partição e validar as contagens.

## Qualidade
```bash
ruff check .           # lint
ruff format --check .  # formatação
pytest                 # testes unitários (integração excluída por padrão)
pytest -m integration  # testes de integração (exigem PostgreSQL do laboratório)
```

## Reprodução do experimento final

1. Configure `.env`, carregue as variáveis e suba o PostgreSQL de laboratório:

   ```bash
   set -a; source .env; set +a
   docker compose up -d
   ```

2. Confirme a referência e as contagens da massa conforme
   [docs/DADOS_BENCHMARK.md](docs/DADOS_BENCHMARK.md).

3. Para reproduzir uma medição, use o ambiente virtual e mantenha
   `IXO_ALLOWED_SCHEMAS=cnpj`; a aplicação de índices deve ser uma ação explícita
   no laboratório, nunca em produção.

Os tempos registrados são evidências desta execução, não uma promessa de ganho
para toda consulta. O relatório distingue recomendações, índices aplicados e
resultados inconclusivos.
