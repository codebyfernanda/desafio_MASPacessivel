# Estudo: nomes claros, responsabilidades explícitas e comentários sobre decisões.
# Segmentar sem reescrever preserva datas e negações. Os nomes dos métodos
# sobrescritos e seus parâmetros pertencem ao contrato do DeepEval.

"""Segmentação literal: nenhuma data, negação ou fato é reescrito por LLM."""
import re
from deepeval.metrics import AnswerRelevancyMetric

def trechos_literais(texto):
    if isinstance(texto, list):
        if not all(isinstance(trecho_resposta, str) for trecho_resposta in texto):
            raise ValueError("Somente respostas textuais são suportadas.")
        texto = "\n".join(texto)
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("A avaliação exige uma resposta textual não vazia.")
    trechos = re.split(r"(?<=[.!?;])\s+|\n+", texto.strip())
    return [trecho_resposta.strip() for trecho_resposta in trechos if trecho_resposta.strip()]

class RelevanciaLiteral(AnswerRelevancyMetric):
    name = "Answer Relevancy (trechos literais)"

    def _generate_statements(self, actual_output, multimodal=False):
        if multimodal:
            raise ValueError("Somente respostas textuais são suportadas.")
        return trechos_literais(actual_output)

    async def _a_generate_statements(self, actual_output, multimodal=False):
        return self._generate_statements(actual_output, multimodal)

