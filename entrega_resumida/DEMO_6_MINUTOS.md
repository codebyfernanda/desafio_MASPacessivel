# Apresentação - até seis minutos

Use os arquivos salvos. Não é necessário chamar a AWS durante a apresentação.

**0:00-0:40 | Apresentação.** Faça sua autodescrição. Conte que o projeto avalia um guia acessível do MASP e que você investigou fidelidade às fontes, uso da ferramenta e resistência a ataques.

**0:40-1:25 | Como funciona.** Mostre o caminho agente → Gateway → Lambda → S3. Qwen3 Next é o agente; DeepSeek-R1 é o juiz local. Abra uma captura com chamada real ao RAG e identifique a sessão nos spans.

**1:25-2:15 | As duas avaliações.** Mostre a tabela do golden no relatório. São as mesmas respostas nas duas frentes, com unidades diferentes: 42 notas AWS e 35 casos DeepEval. Explique os cortes 0,7/0,8/0,8 e o significado de não avaliável.

**2:15-3:25 | Ataque e correção.** Compare o RT07 baseline, que copiou instruções, com a recusa final. Em seguida, mostre o RT08: a tradução ainda expôs o prompt. A correção funcionou em parte; esse limite precisa aparecer.

**3:25-4:25 | O juiz também pode errar.** Use o caso 28: o agente atribuiu a obra à artista errada e recebeu G-Eval 1,0. Compare com a Obra 9 da base, de Larissa de Souza. A nota original foi mantida e o problema foi registrado na análise.

**4:25-5:20 | Resultados.** Relevância 21/35→23/35 e conformidade 32/35→33/35. A fidelidade AWS caiu e a cobertura B passou de 26 para 25. No red teaming, G-Eval 10/15→14/15. Explique por que não colocaria o protótipo em produção sem supervisão.

**5:20-6:00 | Aprendizado.** Conte como a releitura do enunciado revelou que os experimentos iniciais comparavam agentes diferentes. Você corrigiu a metodologia e preservou o histórico. Conclua com o que aprendeu sobre requisito, evidência e risco, sem prometer segurança total.

Este é o roteiro. O ensaio e a apresentação precisam ser realizados e cronometrados por você.
