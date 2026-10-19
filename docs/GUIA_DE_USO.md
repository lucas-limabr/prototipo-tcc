# Guia de uso

Este guia cobre a preparação do laboratório, a análise de consultas e o uso da
massa CNPJ com o `index-optimizer`. A aplicação de índices e a carga de dados
alteram o banco: use somente o PostgreSQL local de laboratório, nunca produção.

## Preparar o ambiente

Requisitos: Python 3.11 ou superior e Docker. Na raiz do repositório:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
```

Edite `.env` com os valores locais do laboratório; não compartilhe nem versione
esse arquivo. Para disponibilizar as variáveis no shell e iniciar o banco:

```bash
set -a; source .env; set +a
docker compose up -d
docker compose ps
```

O host e a porta locais padrão são `localhost:55432`. O Compose mantém os dados
persistentes do PostgreSQL em
`/home/lucaslima/Compartilhada/DadosTCC2/postgres-data` e monta
`/home/lucaslima/Compartilhada/DadosTCC2/cnpj-data` como `/data:ro` no
contêiner. Não apague nem remova esses diretórios/volumes como procedimento de
limpeza.

As variáveis reconhecidas pelo CLI são `IXO_ENVIRONMENT`, `IXO_DB_HOST`,
`IXO_DB_PORT`, `IXO_DB_NAME`, `IXO_DB_USER`, `IXO_DB_PASSWORD`,
`IXO_ALLOWED_SCHEMAS`, `IXO_STATEMENT_TIMEOUT_MS`, `IXO_LOCK_TIMEOUT_MS` e
`IXO_CONNECT_TIMEOUT_S`. Para as consultas do conjunto CNPJ, configure
`IXO_ALLOWED_SCHEMAS=cnpj` no ambiente do comando.

## Usar o CLI

Confira a instalação e a conexão:

```bash
index-optimizer --help
index-optimizer analyze --help
index-optimizer benchmark --help
index-optimizer optimize --help
index-optimizer cleanup --help
index-optimizer --version
index-optimizer check-connection
```

Os comandos que recebem consulta exigem exatamente uma fonte: `--query SQL` ou
`--query-file PATH`, e aceitam somente uma consulta de leitura. Exemplo de consulta:

```bash
export IXO_ALLOWED_SCHEMAS=cnpj
index-optimizer analyze --query \
  "SELECT e.cnpj_basico FROM cnpj.estabelecimento AS e WHERE e.uf = 'SP'"
```

Também é possível guardar o SQL em um arquivo e passar seu caminho:

```bash
index-optimizer analyze --query-file consultas/filtro-uf.sql
```

### Analisar e medir

- `analyze` valida a consulta, obtém o plano estimado e apresenta recomendações.
  É somente leitura e não altera a estrutura do banco.
- `benchmark` mede a consulta com `EXPLAIN ANALYZE`, sem aplicar alterações.
  O padrão é cinco medições e um aquecimento; ajuste com `--runs` e `--warmup`:

  ```bash
  index-optimizer benchmark --query \
    "SELECT e.cnpj_basico FROM cnpj.estabelecimento AS e WHERE e.uf = 'SP'" \
    --runs 5 --warmup 1
  ```

Os comandos de consulta imprimem relatórios JSON em `stdout`. O comando
`check-connection` imprime informações de conexão em texto. Nenhum comando
salva automaticamente arquivos de relatório. Para guardar uma saída, redirecione
o `stdout` explicitamente, por exemplo:

```bash
mkdir -p reports
index-optimizer analyze --query \
  "SELECT e.cnpj_basico FROM cnpj.estabelecimento AS e WHERE e.uf = 'SP'" \
  > reports/analyze-filtro-uf.json
```

Os diretórios `data/` e `reports/` são ignorados pelo Git. A evidência histórica
do experimento final, versionada no projeto, está em
[experimentos/fase15-filtro-uf.json](experimentos/fase15-filtro-uf.json).

### Gerar ou aplicar recomendações

`optimize` usa `--dry-run` por padrão. O modo padrão imprime o DDL proposto e o
relatório JSON, sem criar índices:

```bash
index-optimizer optimize --query \
  "SELECT e.cnpj_basico FROM cnpj.estabelecimento AS e WHERE e.uf = 'SP'"
```

Somente após revisar a recomendação, a aplicação pode ser autorizada
explicitamente no laboratório:

```bash
index-optimizer optimize --query \
  "SELECT e.cnpj_basico FROM cnpj.estabelecimento AS e WHERE e.uf = 'SP'" \
  --apply-indexes
```

A aplicação cria índices B-tree de uma única coluna e executa `ANALYZE` na
tabela. Executar novamente não cria outro índice equivalente: o resultado indica
`SKIPPED_EXISTING`, mas o índice existente permanece no PostgreSQL. Portanto,
uma execução posterior não representa uma linha de base sem índice. Embora
`optimize` aceite `--runs`, essa opção não é usada atualmente. A aplicação não
executa automaticamente um benchmark antes e depois.

Para remover os índices experimentais criados pelo protótipo, use o subcomando
de limpeza com a confirmação explícita:

```bash
index-optimizer cleanup --experimental-indexes
```

Essa operação só é permitida quando `IXO_ENVIRONMENT=lab` e o host é local
(`localhost`, `127.0.0.1` ou `::1`). Ela procura apenas índices cujo nome começa
com `ixo_`, cujo nome corresponde ao padrão determinístico do protótipo, e que
sejam B-tree simples de uma coluna. Índices de chave primária, `UNIQUE`,
exclusão, identidade de réplica, parciais ou baseados em expressões nunca são
removidos. A seleção e os `DROP INDEX` ocorrem na mesma transação, com
identificadores delimitados pelo driver.

O comando sempre imprime JSON com `status`, `removed_count` e
`removed_indexes`. Quando não há índices elegíveis, termina com sucesso e
informa `removed_count: 0`; não há procedimento genérico destrutivo de reset.

O resultado registrado em
[experimentos/fase15-filtro-uf.json](experimentos/fase15-filtro-uf.json) é
evidência histórica de um único experimento: o índice
`ixo_estabelecimento_uf_idx_f71e437d` foi associado a medianas de 854,946 ms
antes e 802,909 ms depois, redução observada de 6,09%. Esses números não são
garantidos nem reproduzidos automaticamente por uma nova execução. Consulte
[METODOLOGIA_EXPERIMENTO.md](METODOLOGIA_EXPERIMENTO.md) para protocolo,
condições e limitações.

Para uma comparação pré/pós realmente nova, comece de uma cópia de segurança ou
snapshot apropriado, ou prepare o laboratório isolado por um processo seguro e
documentado pelo DBA. Não há neste guia um procedimento genérico destrutivo de
reset.

### Códigos de saída do CLI principal

| Código | Significado |
|---:|---|
| 0 | Sucesso |
| 1 | Erro inesperado |
| 2 | Entrada ou configuração inválida |
| 3 | Falha de conexão |
| 4 | Consulta não suportada |
| 5 | Timeout |
| 6 | Falha ao aplicar índice |

Esses códigos descrevem o CLI `index-optimizer`; o módulo de dados pode retornar
códigos próprios em caso de falha.

## Baixar, carregar e validar a massa CNPJ

O módulo é executado com `python -m index_optimizer.datasets.cnpj`. A opção
global `--data-dir` deve vir antes do subcomando. O diretório padrão é
`data/cnpj`; arquivos baixados ficam em `<data-dir>/<referência>/` e incluem
`manifest.json` com hashes SHA-256. Dados locais não são versionados pelo Git.

Baixe uma referência mensal e uma partição de estabelecimentos:

```bash
python -m index_optimizer.datasets.cnpj \
  --data-dir data/cnpj download --reference 2026-10 --parts 1
```

`--parts` aceita valores de 0 a 9 e, se omitido, usa a partição 1. O download
inclui as partições de estabelecimentos escolhidas, todas as partições de
empresas e sócios, e os ZIPs das tabelas de domínio.

Para carregar no PostgreSQL, primeiro carregue `.env` no shell e confirme que o
PostgreSQL de laboratório está ativo. A carga limitada abaixo requer os dois
limites juntos e seleciona estabelecimentos da primeira partição indicada no
manifesto:

```bash
set -a; source .env; set +a
python -m index_optimizer.datasets.cnpj \
  --data-dir data/cnpj load --reference 2026-10 \
  --max-companies 1000000 --max-establishments 1000000
python -m index_optimizer.datasets.cnpj \
  --data-dir data/cnpj validate
```

Sem limites, `load` importa os arquivos listados no manifesto. A carga normal
trunca as tabelas de dados gerenciadas do schema `cnpj` antes de importar, mas
não remove índices. `--resume` evita essa truncagem e reprocessa os arquivos
pelas regras de conflito de cada inserção (atualizando ou ignorando registros
existentes, conforme a tabela e o modo de carga). Em ambos os modos, a carga não
restaura o conteúdo anterior do banco, não redefine o estado original do catálogo
e não remove índices experimentais. Em particular, `TRUNCATE` preserva índices;
repetir a carga não desfaz aplicações anteriores nem recupera automaticamente os
dados que foram substituídos. A opção `validate` imprime verificações de contagem
e integridade.

Veja [DADOS_BENCHMARK.md](DADOS_BENCHMARK.md) para detalhes da fonte, dos dados,
do procedimento e das limitações da massa.
