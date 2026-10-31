# PTOSS 2 — testes de `generate_fallback_webarchive_url`

Responsável: Maria Eduarda Rodrigues Morais. Execuções: 25/10/2026.

Base da equipe: [xLucasMelo/linkding, dddd54b](https://github.com/xLucasMelo/linkding/commit/dddd54b81fe5156ced0071f6b3cd00d074a2cd30), Linkding 1.46.2. Não houve mudança no código de produção. Os metadados registram essa base porque as execuções ocorreram antes do primeiro commit dos arquivos novos.

## Função e testes anteriores

`bookmarks/services/wayback.py` monta uma URL do Internet Archive com a data no formato `YYYYmmddHHMMSS`, preservando a URL original. Retorna `None` para URL ausente e consulta `timezone.now()` quando falta a data. A função é usada na serialização dos bookmarks e nos contextos da interface. Ela não valida a URL, não consulta a rede e não verifica a existência de um snapshot.

O teste de integração `BookmarksApiTestCase.test_get_bookmark_returns_fallback_webarchive_url`, em `bookmarks/tests/test_bookmarks_api.py`, já verificava a URL com data informada. A execução anterior aos novos testes não cobria o retorno antecipado nem a consulta ao relógio.

## Caixa-preta: classes de equivalência

| Classe | Condição | Tipo | Saída esperada |
| --- | --- | --- | --- |
| E1 | URL não vazia | Válida | URL do arquivo com sufixo original intacto |
| E2 | URL vazia | Inválida para gerar endereço; tratada | `None` |
| E3 | URL `None` | Fora da anotação `str`; comportamento defensivo existente | `None` |
| E4 | `datetime` informado | Válida | Data informada com precisão de segundos |
| E5 | Data `None` | Ausência tratada pela função | Data atual fornecida pelo relógio |

Não se atribui validação sintática de URLs à função. Strings malformadas, tipos arbitrários, conversão de fuso e indisponibilidade do Internet Archive não são requisitos testados aqui.

| Caso | Classes / limites | Entrada | Resultado esperado |
| --- | --- | --- | --- |
| CP01 | E1, E4 | `https://example.com/`, 11/08/2023 21:45:11 UTC | Prefixo `20230811214511` e URL original |
| CP02 | E1, E4 | HTTP; HTTPS com caixa, porta, query, fragmento; Unicode | Preservação exata das três URLs |
| CP03 | E2, E4 | URL vazia e data válida | `None` |
| CP04 | E3, E4 | URL `None` e data válida | `None` |
| CP05 | E1, E4 | 02/01/2026 00:00:00 UTC | `20260102000000` |
| CP06 | E1, E4 | Último segundo de 1999 e primeiro de 2000 | `19991231235959`; `20000101000000` |
| CP07 | E1, E4 | 28/02 → 29/02 → 01/03 de 2024, nos limites do dia | Data preservada nos quatro valores |
| CP08 | E1, E4 | Microssegundos 0, 1 e 999999 no último segundo de 2026 | `20261231235959`, sem arredondamento |

## Caixa-branca: decisões e caminhos

D1 é `not url` (linha 15); D2 é `not timestamp` (linha 17). Cada decisão tem uma única condição. Não há decisão composta que exija tabela MC/DC com várias condições; variar a única condição já varia a decisão. D2 só é alcançada quando D1 é falsa. A complexidade ciclomática é 3 e há três caminhos viáveis.

| Caso | D1 | D2 | Verificação |
| --- | --- | --- | --- |
| CB01 | Verdadeira | Não alcançada | URL vazia e data ausente retornam `None`, sem consultar o relógio |
| CB02 | Falsa | Falsa | Data informada é usada; relógio não é consultado |
| CB03 | Falsa | Verdadeira | Data ausente usa uma única chamada a `timezone.now()` |
| CB04 | Falsa | Verdadeira, em duas chamadas | Data é recalculada a cada chamada, inclusive na virada do ano |

O mock substitui somente o relógio externo no namespace da função. A função sob teste permanece real. Os casos de caixa-preta verificam o contrato de saída e os limites; os de caixa-branca complementam a cobertura do fluxo e dos efeitos sobre o relógio.

## Implementação e reprodução

Código completo: [test_wayback.py](../../../bookmarks/tests/test_wayback.py). Runner: [run_wayback_coverage.py](../../../scripts/run_wayback_coverage.py).

Use um ambiente do projeto com as dependências de desenvolvimento. [requirements-tested.txt](requirements-tested.txt) registra as versões do ambiente utilizado; não substitui o arquivo de dependências oficial. O ambiente Windows desta execução não inclui `uwsgi`.

```sh
python scripts/run_wayback_coverage.py baseline
python scripts/run_wayback_coverage.py new
python scripts/run_wayback_coverage.py combined
```

O runner usa SQLite em memória, fila Huey em arquivo temporário e hasher MD5 somente no processo de testes. Mede linhas e branches de `bookmarks.services.wayback` com `coverage.py`; gera logs, JSON, HTML e metadados em `output/relatorio2-wayback/`. `baseline` ignora apenas o novo arquivo; `new` executa somente esse arquivo; `combined` inclui todos os testes de `bookmarks/tests`.

## Resultados reais

Ambiente: Windows, Python 3.13.16, Django 6.1.2, pytest 9.1.1, pytest-django 4.14.0 e coverage 7.16.2.

| Execução | Resultado |
| --- | --- |
| Antes | 1295 aprovados, 5 falhas, 1 erro; 58 subtestes aprovados; 110,46 s |
| Somente novos | 12 aprovados e 12 subtestes aprovados; 2,88 s |
| Combinada | 1308 aprovados, 4 falhas; 70 subtestes aprovados; 114,53 s |

Os quatro casos de `SingleFileServiceTestCase` abaixo falham no encerramento por `PermissionError: [WinError 32]`, ao tentar excluir arquivo temporário ainda aberto no Windows:

- `test_create_snapshot_custom_options`
- `test_create_snapshot_custom_timeout_setting`
- `test_create_snapshot_default_timeout_setting`
- `test_create_snapshot_empty_options`

Todos já falhavam na execução anterior. `MonolithServiceTestCase.test_create_snapshot` também apresentou falha e erro de limpeza no baseline, mas passou na execução combinada. Essa diferença indica variabilidade da infraestrutura; não se afirma que a suíte completa passou. A comparação dos identificadores não encontrou teste com falha novo na execução combinada. Não foram alterados esses serviços para esta atividade.

| Escopo | Antes: linhas | Antes: branches | Depois: linhas / branches |
| --- | --- | --- | --- |
| Função escolhida | 3/5 (60%) | 2/4 (50%) | 5/5 e 4/4 (100%) |
| Arquivo `wayback.py` | 6/8 (75%) | 2/4 (50%) | 8/8 e 4/4 (100%) |

O `Cover` de 67% mostrado no terminal combina linhas e branches do arquivo inteiro: (6 + 2)/(8 + 4). Na função, o índice combinado anterior era (3 + 2)/(5 + 4) = 55,56%. A comparação correta separa função/arquivo e linhas/branches. Cobertura de 100% não comprova ausência de defeitos ou disponibilidade do serviço externo.

## Evidências e limites

[Evidências](evidencias/) contém os JSON originais de cobertura e metadados; os logs `baseline-resultado.txt` e `combined-resultado.txt` são excertos da seção final dos logs reais; `new-resultado.txt` contém a execução dos testes novos. [summary.json](evidencias/summary.json) consolida as métricas. [execucoes.png](evidencias/execucoes.png) é uma captura do visualizador HTML dos logs reais, explicitamente identificado como tal, sem simulação de terminal.

As execuções validam somente o ambiente indicado. O baseline com falhas limita conclusões sobre a saúde global do projeto. Os testes cobrem o comportamento atual da função, sem chamadas de rede e sem implementação de funcionalidade nova. Esta contribuição é caixa-preta/caixa-branca; não constitui a etapa de TDD da equipe e não apresenta ciclos red/green fabricados.

## Uso de IA

Na contribuição de Maria Eduarda, houve assistência do Codex na análise do código, no projeto e implementação dos casos, na automação das execuções, na interpretação dos resultados e na redação do relatório. Os números apresentados foram obtidos por execuções reais. Essa declaração se restringe a esta contribuição e não atribui uso de IA aos demais integrantes.
