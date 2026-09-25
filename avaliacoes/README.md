# Avaliações do guia MASP

Esta pasta reúne o código usado na campanha e os resultados das duas frentes. Os dados já foram avaliados: 35 casos golden e 15 ataques, antes e depois da correção do prompt.

## Arquivos principais

| Arquivo ou pasta | Uso |
|---|---|
| config/prompt_baseline.md e prompt_final.md | Instruções do agente em cada versão |
| config/baseline.json e final.json | Modelo, ferramenta e limites |
| dados/golden_dataset.json | 35 casos, sete por categoria |
| dados/redteam/ataques.json | 15 tentativas de ataque |
| dados/base_conhecimento_manifesto.json | Registro da base utilizada |
| campanha.py | Captura respostas, exporta spans e chama os avaliadores AWS |
| src/agent_core/lambda_avaliador.py | Regras do avaliador customizado |
| test_qwen.py e avaliacao.py | Suíte DeepEval sobre as capturas |
| src/deepeval/juiz.py | Adaptação do DeepSeek-R1 local |
| recuperar_deepeval.py | Recuperação apenas de avaliações com timeout |
| comparar.py | Consolidação dos resultados das duas frentes |

## Como ler os resultados

Na **frente A**, `golden_baseline.json` e arquivos equivalentes guardam perguntas, respostas, sessões e eventos. `spans_*.json` contém os rastros exportados da AWS. `avaliacao_*.json` contém notas e justificativas dos avaliadores.

Na **frente B**, a comparação usa `golden_baseline_recuperacao.json`, `golden_final_recuperacao.json`, `redteam_baseline.json` e `redteam_final.json`. Os arquivos originais do golden ficaram preservados porque houve timeouts. Só as métricas com erro foram repetidas; notas válidas, inclusive reprovações, não foram refeitas.

Os JSONL são a gravação incremental de cada rodada. Não os apague: eles permitem conferir o que estava salvo antes de uma interrupção.

A comparação está em `resultados/revisao/comparacao_20260925T130832760234Z.csv` e no JSON de mesmo nome. A tabela completa de achados fica em `../entrega_resumida/RED_TEAMING_15.csv`.

## Ambiente e execução

Abra o terminal **nesta pasta**, depois de extrair o ZIP. O ambiente virtual não acompanha a entrega.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Para verificar o código, sem chamar AWS ou juiz:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Para gerar outra comparação a partir dos arquivos salvos, sem novas avaliações:

```powershell
.\.venv\Scripts\python.exe comparar.py
```

As etapas abaixo documentam a execução da campanha. Os arquivos encerrados são protegidos contra sobrescrita; não apague os resultados para refazer uma rodada.

```powershell
.\.venv\Scripts\python.exe campanha.py capturar golden baseline
.\.venv\Scripts\python.exe campanha.py spans golden baseline
.\.venv\Scripts\python.exe campanha.py avaliar-a golden baseline
```

Para o DeepEval, o comando usado foi:

```powershell
$env:MASP_QWEN_TIPO = "golden"
$env:MASP_QWEN_VERSAO = "baseline"
$env:DEEPEVAL_PER_TASK_TIMEOUT_SECONDS_OVERRIDE = "1200"
$env:DEEPEVAL_RETRY_MAX_ATTEMPTS = "1"
.\.venv\Scripts\deepeval.exe test run test_qwen.py -v
```

`TIPO` aceita `golden` ou `redteam`; `VERSAO`, `baseline` ou `final`. A execução depende do Ollama com o digest do juiz registrado nos logs. Não atualize o modelo no meio da comparação. Para uma rodada parcial, a retomada usa `MASP_QWEN_RETOMAR=1`; ela não altera notas já registradas. Timeouts encerrados têm recuperação separada, com `recuperar_deepeval.py golden baseline` ou `golden final`.

As capturas AWS precisam de login válido no perfil e acesso aos recursos configurados em `config/`. Esses recursos pertencem à conta usada no projeto; o pacote não os cria em outra conta. Novas capturas e avaliações AWS podem gerar cobrança. Os comandos completos de preparação estão preservados no histórico, em `documentacao_anterior_qwen/LEIA_PRIMEIRO.md`.

## Limites que importam na leitura

Faithfulness sem contexto recuperado fica **não avaliável**. Aprovado em uma métrica não significa seguro. Os resultados de red teaming precisam ser lidos junto das respostas e da severidade. Os quinze ataques finais foram avaliados; a conclusão do projeto está no relatório, não apenas na taxa mostrada pelo terminal.
