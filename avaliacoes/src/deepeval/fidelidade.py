# Estudo: nomes claros, responsabilidades explícitas e comentários sobre decisões.
# O adaptador muda a preparação da evidência, mas preserva a fórmula,
# os veredictos e os thresholds do DeepEval. Não atribui aprovação por conta própria.

"""Faithfulness do DeepEval com referência integral, sem resumo intermediário.

Mantém os vereditos por LLM, a fórmula e o threshold da biblioteca.
Segmenta as afirmações em trechos literais, sem reescrevê-las com outro LLM.
A referência já é recuperada em trechos curtos pelo RAG. Reescrevê-la com outro
LLM pode alterar os fatos usados para julgar a resposta (por exemplo, horários).
"""
from deepeval.metrics import FaithfulnessMetric
from .extracao import trechos_literais

class FidelidadeFonteIntegral(FaithfulnessMetric):
    name = "Faithfulness (fontes integrais)"

    def _generate_truths(self, retrieval_context, multimodal=False):
        if multimodal:
            raise ValueError("Esta implementação avalia somente fontes textuais.")
        if not retrieval_context or not all(isinstance(trecho_fonte, str) and trecho_fonte.strip() for trecho_fonte in retrieval_context):
            raise ValueError("A avaliação exige fontes textuais não vazias.")
        return list(retrieval_context)

    async def _a_generate_truths(self, retrieval_context, multimodal=False):
        return self._generate_truths(retrieval_context, multimodal)

    def _generate_claims(self, actual_output, multimodal=False):
        if multimodal:
            raise ValueError("Somente respostas textuais são suportadas.")
        return trechos_literais(actual_output)

    async def _a_generate_claims(self, actual_output, multimodal=False):
        return self._generate_claims(actual_output, multimodal)

