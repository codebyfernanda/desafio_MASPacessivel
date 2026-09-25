# MASP Acessível

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

## O que foi avaliado

O agente é **Qwen3 Next 80B A3B**, executado no AgentCore. A frente A usa Helpfulness, Faithfulness e um avaliador customizado de regras do domínio. A frente B avalia as mesmas respostas com DeepEval e o juiz local **DeepSeek-R1**.

As execuções terminaram. Os resultados estão salvos; não é necessário rodar tudo novamente para apresentar o projeto. O relatório registra as melhorias e as falhas que permaneceram, incluindo a tradução de instruções internas no RT08 e a autoria incorreta no caso 28.

O histórico reúne Gemma, Qwen 2.5, o relatório anterior e os 45 testes de código do projeto anterior. Os 14 testes do complemento Qwen são adicionais. A base e seu manifesto foram mantidos em `avaliacoes/dados/`.

Esta reorganização mudou a localização da pasta de trabalho e reduziu a documentação repetida. Código, prompts, datasets e resultados brutos da campanha principal foram preservados. Os caminhos citados dentro do relatório e dos logs são relativos à pasta `avaliacoes`, salvo os documentos de `entrega_resumida`.

`manifesto.json` permite conferir a integridade dos arquivos. O histórico mantém a anotação de sete logs antigos com identificadores de credenciais ocultados na cópia compartilhável; nenhum resultado de avaliação foi alterado por isso.
