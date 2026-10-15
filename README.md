# index-optimizer

Protótipo de pesquisa do TCC **“Otimização de Bancos de Dados Relacionais: Indexação
Automatizada para Maximização de Performance”**. Analisa consultas `SELECT` no PostgreSQL,
recomenda índices por regras explícitas e, apenas em um banco de laboratório, permite
aplicá-los e comparar o desempenho antes/depois.

> Estado atual: preparação da massa CNPJ (Fase 4). Os subcomandos de análise
> ainda não executam consultas.
> Veja [docs/STATUS_DESENVOLVIMENTO.md](docs/STATUS_DESENVOLVIMENTO.md).

## Requisitos
- Python ≥ 3.11
- Docker (a partir da Fase 3)

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

## Documentação
- [Arquitetura](agents/docs/ARQUITETURA.md)
- [Decisões técnicas](agents/docs/DECISOES_TECNICAS.md)
- [Plano de execução](agents/docs/PLANO_EXECUCAO_PROTOTIPO_INDEXACAO_AUTOMATIZADA.md)
