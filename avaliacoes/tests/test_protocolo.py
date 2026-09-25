"""Verificações locais. Não avaliam a qualidade do agente e não chamam a AWS."""
import hashlib
import json
import pytest
from campanha import casos, configuracao, gravar
from evidencias_rag import summarize, SOURCE, TOOL
from avaliacao import contextos


def eventos(body='Fonte real de teste', status='success', cid='u1', rid='u1', digest=None):
    retorno = json.dumps({'fonte': SOURCE, 'conteudo': body,
                          'sha256': digest or hashlib.sha256(body.encode()).hexdigest()})
    return [
        {'messageStart': {'role': 'assistant'}},
        {'contentBlockStart': {'contentBlockIndex': 0, 'start': {'toolUse': {'toolUseId': cid, 'name': TOOL}}}},
        {'contentBlockDelta': {'contentBlockIndex': 0, 'delta': {'toolUse': {'input': '{"consulta":"MASP"}'}}}},
        {'messageStop': {'stopReason': 'tool_use'}},
        {'messageStart': {'role': 'user'}},
        {'contentBlockStart': {'contentBlockIndex': 0, 'start': {'toolResult': {'toolUseId': rid, 'status': status}}}},
        {'contentBlockDelta': {'contentBlockIndex': 0, 'delta': {'toolResult': [{'text': retorno}]}}},
        {'messageStop': {'stopReason': 'end_turn'}},
        {'messageStart': {'role': 'assistant'}},
        {'contentBlockDelta': {'contentBlockIndex': 0, 'delta': {'text': 'Resposta com referência.'}}},
        {'messageStop': {'stopReason': 'end_turn'}},
    ]


def test_casos_e_limites():
    assert len(casos('golden')) == 35
    assert [c['id'] for c in casos('redteam')] == [f'RT{i:02}' for i in range(1, 16)]
    assert len({c['categoria'] for c in casos('redteam')}) >= 4
    assert len(casos('piloto')) == 5
    cfg = configuracao('baseline')['overrides']
    assert cfg['model']['bedrockModelConfig']['modelId'] == 'qwen.qwen3-next-80b-a3b-instruct'
    assert cfg['allowedTools'] == ['@masp-rag/' + TOOL]


def test_retorno_real_correlacionado():
    a = summarize(eventos())
    assert a['solicitacao_e_retorno_rag_observados']
    assert contextos({'analises_por_turno': [a]}) == ['Fonte real de teste']


@pytest.mark.parametrize('alteracao', [{'status': 'error'}, {'rid': 'outro'}, {'digest': 'adulterado'}])
def test_retorno_invalido_nao_vira_fonte(alteracao):
    a = summarize(eventos(**alteracao))
    assert not a['solicitacao_e_retorno_rag_observados']
    assert contextos({'analises_por_turno': [a]}) == []


def test_texto_tool_code_nao_e_chamada():
    a = summarize([{'messageStart': {}}, {'contentBlockDelta': {'delta': {'text': '```tool_code\nRAG_MASP()\n```'}}}, {'messageStop': {'stopReason': 'end_turn'}}])
    assert not a['solicitacao_e_retorno_rag_observados']


def test_isolamento_contextos():
    primeiro = summarize(eventos(body='Fonte A'))
    segundo = summarize(eventos(body='Fonte B'))
    assert contextos({'analises_por_turno': [primeiro]}) == ['Fonte A']
    assert contextos({'analises_por_turno': [segundo]}) == ['Fonte B']


def test_nao_sobrescreve(tmp_path):
    path = tmp_path / 'resultado.json'
    gravar(path, {'primeiro': True})
    with pytest.raises(FileExistsError):
        gravar(path, {'primeiro': False})


def test_nota_baixa_preservada_sem_repetir(monkeypatch):
    import sys
    from types import SimpleNamespace
    from avaliacao import medir_registrando
    chamadas = []
    metrica = SimpleNamespace(score=0.2, error=None)
    def simular(*args, **kwargs):
        chamadas.append(1)
        raise AssertionError('Nota abaixo do threshold')
    monkeypatch.setitem(sys.modules, 'deepeval', SimpleNamespace(assert_test=simular))
    medir_registrando(metrica, object())
    assert chamadas == [1]
    assert metrica.score == 0.2


def test_erro_tecnico_nao_e_nota_baixa(monkeypatch):
    import sys
    from types import SimpleNamespace
    from avaliacao import medir_registrando
    def simular(*args, **kwargs):
        raise AssertionError('Juiz não retornou nota')
    monkeypatch.setitem(sys.modules, 'deepeval', SimpleNamespace(assert_test=simular))
    with pytest.raises(AssertionError):
        medir_registrando(SimpleNamespace(score=None, error='Falha'), object())
