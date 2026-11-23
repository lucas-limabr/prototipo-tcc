# Massa de dados do benchmark: CNPJ

## Fonte e condições de uso

- **Conjunto:** Cadastro Nacional da Pessoa Jurídica (CNPJ).
- **Órgão responsável:** Receita Federal do Brasil.
- **Portal:** [dados.gov.br — CNPJ](https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica---cnpj).
- **Arquivos:** [compartilhamento oficial da Receita Federal](https://arquivos.receitafederal.gov.br/public.php/webdav/).
- **Formato:** arquivos CSV delimitados por `;`, codificados em Latin-1 e
  distribuídos em arquivos ZIP.
- **Licença/termos:** o conjunto é publicado como dado aberto no portal
  governamental. A reutilização deve preservar a atribuição à Receita Federal
  e observar os termos vigentes na página do conjunto e a legislação aplicável.
- **Privacidade:** os arquivos podem conter dados cadastrais e identificadores
  de pessoas. Use somente o banco Docker local do projeto; não publique os
  arquivos baixados nem relatórios com registros individuais.

O portal publica referências mensais. A referência efetivamente usada no
experimento é registrada em `manifest.json`, junto com tamanho e SHA-256 de
cada arquivo. Assim, a data deste documento não substitui a identificação do
snapshot experimental.

Em 2026-10-13, a referência `2026-10` estava acessível e continha 37 arquivos,
com aproximadamente 7 GiB compactados no total. A seleção `--parts 1` foi
estimada em aproximadamente 2,26 GiB compactados e foi baixada em diretório indicado pelo usuário.

## Modelo carregado

O carregador cria o schema `cnpj` e importa:

- `empresa`: dados básicos da pessoa jurídica;
- `estabelecimento`: estabelecimentos e atributos de localização/atividade;
- `socio`: sócios e representantes;
- tabelas de domínio de CNAE, município, país, natureza jurídica, situação e
  qualificações;
- `carga`: histórico de referência, arquivos, hashes e linhas inseridas.

`estabelecimento` é a tabela principal para os experimentos. A validação exige
ao menos 500.000 linhas e verifica as referências para `empresa`.

## Procedimento reprodutível

1. Suba o laboratório e carregue as variáveis locais:

   ```bash
   cp .env.example .env
   set -a; source .env; set +a
   docker compose up -d
   ```

2. Escolha uma referência mensal exibida no compartilhamento oficial (por
   exemplo, `2026-10`) e baixe as partições necessárias de estabelecimentos:

   ```bash
   python -m index_optimizer.datasets.cnpj \
     --data-dir data/cnpj download --reference 2026-10 --parts 0 1
   ```

   O comando também baixa os dez arquivos `Empresas*.zip`, os dez
   `Socios*.zip` e as tabelas de domínio. O download é retomável e grava
   `data/cnpj/<referencia>/manifest.json`.

3. Execute a carga idempotente no PostgreSQL de laboratório:

   ```bash
   python -m index_optimizer.datasets.cnpj \
     --data-dir /home/lucaslima/Compartilhada/DadosTCC2/cnpj-data \
     load --reference 2026-10 --max-companies 5000000 \
     --max-establishments 5000000
   python -m index_optimizer.datasets.cnpj \
     --data-dir /home/lucaslima/Compartilhada/DadosTCC2/cnpj-data validate
   ```

   Se uma carga for interrompida por falta de espaço, aumente o armazenamento
   e repita o comando com `--resume`. Essa opção preserva as linhas já
   confirmadas e reprocessa os arquivos com upsert, sem truncar as tabelas.
   Para atingir a meta de cinco milhões, o manifesto precisa conter partições
   suficientes de `Estabelecimentos`; os limites são máximos, não garantias.

4. Guarde a saída da validação e o manifesto como evidência local do
   experimento. Não copie os ZIPs ou esses artefatos para o Git.

Para uma carga completa, repita `--parts 0 1 2 3 4 5 6 7 8 9`. Ela exige
centenas de gigabytes de armazenamento temporário em algumas referências e não
é necessária para os testes iniciais.

## Limitações

- O tamanho e a disponibilidade dos arquivos variam por referência mensal.
- As partições escolhidas precisam ser validadas; o carregador não afirma que
  uma referência atende cinco milhões de linhas antes da execução de `validate`.
- A carga usa todas as partições de `Estabelecimentos` listadas no manifesto no
  modo limitado; o download padrão ainda pode selecionar apenas uma partição
  para manter o laboratório reproduzível e viável.
- O schema contém índices mínimos de integridade e acesso. Índices criados pelo
  protótipo serão tratados separadamente nas fases posteriores.
- As datas são convertidas para o tipo PostgreSQL `date`, aceitando
  `YYYYMMDD` e `DDMMYYYY`. Datas impossíveis ou valores críticos da fonte
  resultam em `NULL`; campos vazios opcionais permanecem ausentes.
- A validação de contagem não é uma garantia de completude nacional quando
  apenas uma partição foi importada.
