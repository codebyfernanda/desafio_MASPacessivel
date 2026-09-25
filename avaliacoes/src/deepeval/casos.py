# Estudo: nomes claros, responsabilidades explícitas e comentários sobre decisões.
# Relevância e fidelidade recebem a última resposta; conformidade também
# precisa enxergar os turnos anteriores para verificar o pedido completo.

"""Monta evidências distintas para a última resposta e a conformidade da conversa."""
from deepeval.test_case import LLMTestCase

PAPEL = 'Contexto do atendimento: guia do acervo, da visitação e da acessibilidade do MASP.'


def montar_casos(turnos, respostas, esperado, contexto):
    if not turnos or len(turnos) != len(respostas):
        raise ValueError('Cada turno precisa ter exatamente uma resposta real.')
    historico = '\n'.join(f'Usuário: {turno_conversa}\nAssistente: {resposta_conversa}'
                          for turno_conversa, resposta_conversa in zip(turnos[:-1], respostas[:-1]))
    entrada = f'Histórico:\n{historico}\nPergunta atual: {turnos[-1]}' if historico else turnos[-1]
    ultima = LLMTestCase(input=f'{PAPEL}\n\n{entrada}', actual_output=respostas[-1],
                        expected_output=esperado, retrieval_context=contexto)
    if len(turnos) == 1:
        return ultima, ultima
    perguntas = '\n'.join(f'T{numero_turno}: {turno_conversa}' for numero_turno, turno_conversa in enumerate(turnos, 1))
    saidas = '\n\n'.join(f'T{numero_turno} — resposta do assistente:\n{resposta_conversa}' for numero_turno, resposta_conversa in enumerate(respostas, 1))
    conversa = LLMTestCase(
        input=f'{PAPEL}\nAvalie o cumprimento do critério nos turnos correspondentes da conversa.\n{perguntas}',
        actual_output=saidas, expected_output=esperado, retrieval_context=contexto)
    return ultima, conversa

