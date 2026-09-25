# ✸ Avaliações do Guia MASP

> **Autora:** Fernanda Bastos (@codebyfernanda)
> **Data de Entrega Consolidada:** 25/09/2026

Esta pasta reúne o código utilizado na campanha de testes e os resultados obtidos nas duas frentes de avaliação. Os dados já foram avaliados, contemplando **35 casos de** ***Golden Dataset*** (sete por categoria) e **15 ataques de** ***Red Teaming***, com a comparação das respostas antes (*baseline*) e depois (final) da correção do *prompt*.

---

## ✸ Estrutura de Arquivos

| Arquivo / Pasta | Uso |
|:---:|:---:|
| `config/prompt_baseline.md` e `prompt_final.md` | Instruções do agente em cada versão. |
| `config/baseline.json` e `final.json` | Configurações de modelo, ferramentas e limites da API. |
| `dados/golden_dataset.json` | 35 casos de teste validados (golden), separados por categoria. |
| `dados/redteam/ataques.json` | 15 tentativas estruturadas de ataque. |
| `dados/base_conhecimento_manifesto.json` | Registro e manifesto da base de conhecimento utilizada. |
| `campanha.py` | Script principal para capturar respostas, exportar rastros (spans) e acionar avaliadores da AWS. |
| `src/agent_core/lambda_avaliador.py` | Regras do avaliador customizado rodando em função Lambda. |
| `test_qwen.py` e `avaliacao.py` | Suíte do DeepEval executada sobre as capturas. |
| `src/deepeval/juiz.py` | Adaptação para o uso do modelo local (DeepSeek-R1). |
| `recuperar_deepeval.py` | Utilitário para reavaliar apenas itens que sofreram timeout no DeepEval. |
| `comparar.py` | Utilitário para consolidação dos resultados de ambas as frentes. |

---

## ✸ Como Ler os Resultados

### ✸ Frente A (***AWS AgentCore Evaluations***)
* **Capturas:** Arquivos como `golden_baseline.json` armazenam as perguntas, respostas do modelo, sessões e eventos.
* **Rastros:** Os arquivos `spans_*.json` contêm a árvore de execução exportada da AWS.
* **Avaliações:** Os arquivos `avaliacao_*.json` detalham as notas e justificativas dadas pelos avaliadores.

### ✸ Frente B (***DeepEval*** local)
* A comparação consolidada utiliza os arquivos de recuperação e de ataques: `golden_baseline_recuperacao.json`, `golden_final_recuperacao.json`, `redteam_baseline.json` e `redteam_final.json`.
* **Tratamento de timeouts:** Os arquivos originais do conjunto golden foram preservados intactos após falhas de tempo limite. Somente as métricas com erro (timeout) foram repetidas. Notas válidas anteriores, incluindo reprovações, não foram refeitas.
* **Histórico de Execução:** Os arquivos `.jsonl` formam o log de gravação incremental de cada rodada. **Não os apague**, pois eles permitem restaurar o progresso em caso de interrupção.

### ✸ Relatórios Finais
* A comparação das frentes encontra-se em `resultados/revisao/comparacao_20260925T130832760234Z.csv` (e no arquivo `.json` de mesmo nome).
* A tabela completa com os achados de segurança e vulnerabilidades fica em `../entrega_resumida/RED_TEAMING_15.csv`.

---

## ✸ Ambiente & Execução

O ambiente virtual do Python não acompanha esta entrega e deve ser criado localmente. Abra o terminal na raiz desta pasta extraída e execute:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

```

### ✸ Comandos de Validação Rápida

Para validar os *scripts* sem chamar a AWS ou instigar os juízes LLM (não gera custos):

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q

```

Para regerar os arquivos de comparação a partir das execuções já salvas:

```powershell
.\.venv\Scripts\python.exe comparar.py

```

### ✸ Execução da Campanha (Frente A)

Os arquivos resultantes já encerrados estão protegidos contra sobrescrita acidental. Para realizar uma rodada inédita (após alterar arquivos base ou de configuração), a sequência é:

```powershell
.\.venv\Scripts\python.exe campanha.py capturar golden baseline
.\.venv\Scripts\python.exe campanha.py spans golden baseline
.\.venv\Scripts\python.exe campanha.py avaliar-a golden baseline

```

> **Nota de Infraestrutura:** As chamadas à AWS dependem de credenciais válidas e de recursos já instanciados na conta mapeada em `config/`. O pacote não cria esses recursos dinamicamente, e as execuções podem incorrer em cobranças. Comandos de setup anteriores constam em `documentacao_anterior_qwen/LEIA_PRIMEIRO.md`.

### ✸ Execução da Suíte ***DeepEval*** (Frente B)

O DeepEval usa o Ollama local com o juiz LLM. A configuração é feita por variáveis de ambiente. **Aviso:** Não altere a versão do modelo no Ollama durante uma bateria de testes, para não invalidar o comparativo do juiz.

```powershell
$env:MASP_QWEN_TIPO = "golden"
$env:MASP_QWEN_VERSAO = "baseline"
$env:DEEPEVAL_PER_TASK_TIMEOUT_SECONDS_OVERRIDE = "1200"
$env:DEEPEVAL_RETRY_MAX_ATTEMPTS = "1"

.\.venv\Scripts\deepeval.exe test run test_qwen.py -v

```

* `$env:MASP_QWEN_TIPO` aceita `golden` ou `redteam`.
* `$env:MASP_QWEN_VERSAO` aceita `baseline` ou `final`.
* **Retomada:** Em caso de queda, defina `$env:MASP_QWEN_RETOMAR=1` antes de reexecutar. Isso fará o script pular itens com nota já salva.
* **Recuperação manual:** Para timeouts isolados, use `.\.venv\Scripts\python.exe recuperar_deepeval.py golden baseline` ou `final`.

---

## ✸ Interpretação de Limites na Avaliação

1. **Dependência de Contexto:** A métrica de *Faithfulness* (Fidelidade) restará "Não Avaliável" caso o modelo-base responda sem ter recuperado nenhum contexto da base de dados indexada.
2. **Taxa de Aprovação:** O fato de uma resposta ser aprovada matematicamente em uma métrica automatizada não garante que o prompt seja absolutamente seguro contra ataques de prompt injection ou jailbreak.
3. **Análise de Red Teaming:** Os resultados e aprovações da etapa de red teaming (15 ataques) exigem validação qualitativa das respostas e de sua severidade. A conclusão final do projeto baseia-se na avaliação descrita no relatório PDF anexo, e não unicamente na taxa de sucesso registrada pelo terminal.

---

## ✸ Autoria

Este projeto foi desenvolvido por **Fernanda Bastos dos Santos** ([@codebyfernanda](https://github.com/codebyfernanda?utm_source=gemini)), estudante de Análise e Desenvolvimento de Sistemas no Mackenzie, durante o **ESTÁGIO | AWS AI FDE DRIVEN QUALITY ENGINEERING** na Compass UOL / [AI/R Company](https://aircompany.ai/pt/home/).

```

<ElicitationsGroup message="O código markdown já está completo. Quer adicionar mais alguma coisa?">
  <Elicitation label="Criar índice (Sumário)" query="Como eu crio um sumário (Table of Contents) no início deste README para facilitar a navegação?"/>
  <Elicitation label="Revisar texto para o LinkedIn" query="Me ajude a escrever um post para o LinkedIn apresentando este projeto do bootcamp."/>
</ElicitationsGroup>

```
