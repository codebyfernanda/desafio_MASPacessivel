# MASP Acessível

<div align="center">

[![AWS AgentCore](https://img.shields.io/badge/AWS-AgentCore%20%7C%20sa--east--1-FBBC05)](https://aws.amazon.com/bedrock/agentcore/)
![Agente](https://img.shields.io/badge/Agente-Qwen3%20Next%2080B%20A3B-4285F4)
![Arquitetura](https://img.shields.io/badge/Arquitetura-AgentCore%20%2B%20Gateway%20%2B%20Lambda%20%2B%20S3-1967D2)
![Golden Dataset](https://img.shields.io/badge/Golden%20Dataset-35%20casos%20%7C%205%20categorias-F9AB00)
![Frente A](https://img.shields.io/badge/AgentCore%20Evaluations-2%20integrados%20%2B%201%20customizado-4285F4)
![Frente B](https://img.shields.io/badge/DeepEval-3%20m%C3%A9tricas%20%7C%20pytest-1967D2)
![Juiz](https://img.shields.io/badge/Juiz%20local-DeepSeek--R1%20%7C%20Ollama-FBBC05)
![Red Teaming](https://img.shields.io/badge/Red%20Teaming-15%20ataques-EA4335)
![Comparação](https://img.shields.io/badge/An%C3%A1lise-Baseline%20%C3%97%20Final-4285F4)
![Riscos](https://img.shields.io/badge/Status-Falhas%20remanescentes%20documentadas-C5221F)

</div>

Projeto de QA de Fernanda Bastos. Avaliação de um guia do MASP com **35 casos de teste e 15 ataques**, comparando a versão inicial e a versão corrigida nas duas frentes.

## Por onde começar

1. [Relatório de seis páginas](entrega_resumida/RELATORIO_FINAL_6_PAGINAS.pdf): resultados, correções e conclusão.
2. [Tabela dos 15 ataques](entrega_resumida/RED_TEAMING_15.csv): objetivo, técnica, respostas e severidade.
3. [Roteiro da apresentação](entrega_resumida/DEMO_6_MINUTOS.md).
4. [Código e instruções](avaliacoes/README.md).

```text
MASP - Entrega organizada/
├── README.md
├── avaliacoes/
│   ├── config/                 # Modelo, ferramenta e prompts baseline/final
│   ├── dados/                  # Golden 35, ataques 15 e base de conhecimento
│   ├── src/
│   │   ├── agent_core/         # Exportação de spans e avaliadores AWS
│   │   └── deepeval/           # Juiz, métricas e tratamento dos casos
│   ├── tests/                  # Testes do código desta campanha
│   ├── resultados/
│   │   ├── frente_a/           # Capturas, spans e avaliações AgentCore
│   │   ├── frente_b/           # Avaliações DeepEval e recuperações
│   │   └── revisao/            # Comparação, correções e registros do piloto
│   ├── campanha.py            # Captura e avaliação na AWS
│   ├── test_qwen.py           # Suíte DeepEval
│   └── rodada_final.py        # Sequência da rodada final
├── entrega_resumida/
│   ├── RELATORIO_FINAL_6_PAGINAS.pdf
│   ├── RELATORIO.md
│   ├── RED_TEAMING_15.csv
│   └── DEMO_6_MINUTOS.md
└── historico/
    └── experimentos_anteriores.zip
```

A árvore mostra os arquivos principais. Os módulos de apoio continuam na pasta de avaliações.

## Arquitetura do Sistema

```mermaid
flowchart TD
    Usuario(["Usuário"]) -->|Pergunta| Agente

    subgraph AWS["AWS — sa-east-1"]
        Agente["Amazon Bedrock AgentCore<br/>Agente: Qwen3 Next 80B A3B"]
        Sessao["Contexto da sessão<br/>Conversas multi-turno"]
        Gateway["AgentCore Gateway<br/>Ferramenta RAG_MASP"]
        Lambda["AWS Lambda<br/>ler-rag-s3-masp"]
        Base[("Amazon S3<br/>Base de conhecimento do MASP")]
        Logs["CloudWatch<br/>Spans de execução"]

        Agente <-->|Histórico do caso| Sessao
        Agente -->|Solicita consulta| Gateway
        Gateway --> Lambda
        Lambda -->|Lê documento| Base
        Base -->|Conteúdo| Lambda
        Lambda -->|Retorno da ferramenta| Gateway
        Gateway -->|Fonte para responder| Agente
        Agente -->|Registros de execução| Logs
    end

    Agente -->|Resposta| Usuario

    subgraph Campanha["Campanha de QA — baseline e versão final"]
        Golden[("Golden dataset<br/>35 casos / 5 categorias")]
        RedTeam[("Red teaming<br/>15 ataques")]
        Executor["Scripts da campanha"]
        Capturas[("Capturas<br/>Perguntas, respostas, sessões<br/>e retornos do RAG")]

        Golden --> Executor
        RedTeam --> Executor
        Executor -->|Executa os casos| Agente
        Agente -->|Respostas e eventos| Capturas
    end

    subgraph Avaliacoes["Avaliação das mesmas interações em duas frentes"]
        FrenteA["Frente A — AgentCore Evaluations<br/>Builtin.Helpfulness<br/>Builtin.Faithfulness<br/>MaspRegrasDeDominio"]
        FrenteB["Frente B — DeepEval via pytest<br/>Answer Relevancy ≥ 0,7<br/>Faithfulness ≥ 0,8<br/>G-Eval ≥ 0,8"]
        Juiz["Juiz local — Ollama<br/>DeepSeek-R1"]
        Comparacao["Análise baseline × final<br/>Notas, justificativas e vulnerabilidades"]
        Entrega["Relatório, evidências<br/>e demonstração"]

        Logs -->|Spans das sessões| FrenteA
        Capturas -->|Mesmas respostas e contexto registrado| FrenteB
        FrenteB <-->|Avaliação semântica| Juiz
        FrenteA --> Comparacao
        FrenteB --> Comparacao
        Comparacao --> Entrega
    end
```

O Qwen3 Next é o agente avaliado nas duas frentes. O DeepSeek-R1 atua como juiz local do DeepEval. Quando não há contexto recuperado registrado, Faithfulness fica não avaliável nessa frente. Os experimentos anteriores com Gemma e Qwen 2.5 permanecem no histórico.

## O que foi avaliado

O agente é **Qwen3 Next 80B A3B**, executado no AgentCore. A frente A usa Helpfulness, Faithfulness e um avaliador customizado de regras do domínio. A frente B avalia as mesmas respostas com DeepEval e o juiz local **DeepSeek-R1**.

As execuções terminaram. Os resultados estão salvos; não é necessário rodar tudo novamente para apresentar o projeto. O relatório registra as melhorias e as falhas que permaneceram, incluindo a tradução de instruções internas no RT08 e a autoria incorreta no caso 28.

O histórico reúne Gemma, Qwen 2.5, o relatório anterior e os 45 testes de código do projeto anterior. Os 14 testes do complemento Qwen são adicionais. A base e seu manifesto foram mantidos em `avaliacoes/dados/`.

Esta reorganização mudou a localização da pasta de trabalho e reduziu a documentação repetida. Código, prompts, datasets e resultados brutos da campanha principal foram preservados. Os caminhos citados dentro do relatório e dos logs são relativos à pasta `avaliacoes`, salvo os documentos de `entrega_resumida`.

`manifesto.json` permite conferir a integridade dos arquivos. O histórico mantém a anotação de sete logs antigos com identificadores de credenciais ocultados na cópia compartilhável; nenhum resultado de avaliação foi alterado por isso.
