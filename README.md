# index-optimizer

Protótipo de pesquisa do TCC **“Otimização de Bancos de Dados Relacionais: Indexação
Automatizada para Maximização de Performance”**. Analisa consultas `SELECT` no PostgreSQL,
recomenda índices por regras explícitas e, apenas em um banco de laboratório, permite
aplicá-los e comparar o desempenho antes/depois.

> Estado atual: Fase 15 concluída. O protótipo possui validação, análise de
> planos, recomendações, benchmark, aplicação controlada e relatórios.
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

## Reprodução do experimento final

1. Configure `.env`, carregue as variáveis e suba o PostgreSQL de laboratório:

   ```bash
   set -a; source .env; set +a
   docker compose up -d
   ```

2. Confirme a referência e as contagens da massa conforme
   [docs/DADOS_BENCHMARK.md](docs/DADOS_BENCHMARK.md).
3. Consulte o protocolo, as consultas, as condições e as limitações em
   [docs/METODOLOGIA_EXPERIMENTO.md](docs/METODOLOGIA_EXPERIMENTO.md).
4. Consulte o resultado agregado em
   [docs/experimentos/fase15-filtro-uf.json](docs/experimentos/fase15-filtro-uf.json).
5. Para reproduzir uma medição, use o ambiente virtual e mantenha
   `IXO_ALLOWED_SCHEMAS=cnpj`; a aplicação de índices deve ser uma ação explícita
   no laboratório, nunca em produção.

Os tempos registrados são evidências desta execução, não uma promessa de ganho
para toda consulta. O relatório distingue recomendações, índices aplicados e
resultados inconclusivos.

## Documentação
- [Arquitetura](agents/docs/ARQUITETURA.md)
- [Decisões técnicas](agents/docs/DECISOES_TECNICAS.md)
- [Plano de execução](agents/docs/PLANO_EXECUCAO_PROTOTIPO_INDEXACAO_AUTOMATIZADA.md)
- [Metodologia do experimento](docs/METODOLOGIA_EXPERIMENTO.md)
