"""Seleção técnica não autoriza repetir reprovações válidas."""
import pytest
from recuperar_deepeval import selecionar_timeouts


def test_so_timeout_e_selecionado():
    notas = [dict(caso_id='01', metrica='AR', status='avaliado', score=0.1, passou=False),
             dict(caso_id='01', metrica='F', status='nao_avaliavel'),
             dict(caso_id='01', metrica='G', status='erro', erro='TimeoutError: 180s')]
    assert selecionar_timeouts({'resultados': notas}) == {('01', 'G')}
    assert notas[0]['score'] == 0.1


def test_erro_de_outra_causa_exige_revisao():
    with pytest.raises(ValueError):
        selecionar_timeouts({'resultados': [dict(caso_id='01', metrica='G', status='erro', erro='ValueError: JSON inválido')]})


def test_timeout_http_tambem_e_recuperavel():
    assert selecionar_timeouts({'resultados': [dict(caso_id='16', metrica='G-Eval', status='erro', erro='ReadTimeout: timed out')]}) == {('16', 'G-Eval')}


def test_recuperacao_preserva_origem_e_retoma_sem_duplicar(tmp_path, monkeypatch):
    import hashlib
    import json
    import sys
    from types import SimpleNamespace
    import recuperar_deepeval as modulo
    pasta = tmp_path / 'resultados/frente_b'
    pasta.mkdir(parents=True)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    original = pasta / 'golden_baseline.json'
    original.with_suffix('.jsonl').write_text('log original', encoding='utf-8')
    notas = [dict(caso_id='01', metrica='AR', status='avaliado', score=0.1, passou=False),
             dict(caso_id='01', metrica='F', status='nao_avaliavel'),
             dict(caso_id='01', metrica='G', status='erro', erro='TimeoutError: 180s')]
    original.write_text(json.dumps({'metadata': {'status': 'finalizado_com_erros', 'protocolo': 'teste'},
        'log_sha256': sha(original.with_suffix('.jsonl')), 'resultados': notas}), encoding='utf-8')
    antes = sha(original)
    for nome in ('recuperar_deepeval.py', 'test_recuperacao_qwen.py'):
        (tmp_path / nome).write_text('# código de teste', encoding='utf-8')
    def acrescentar(path, valor):
        with path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(valor) + '\n')
    avaliacao_falsa = SimpleNamespace(Rodada=type('Rodada', (), {}), TIPO='golden',
        carregar=lambda _: (tmp_path / 'captura.json', {}, [{'id': '01'}]),
        assinatura=lambda *_: {'protocolo': 'teste'},
        ler=lambda p: json.loads(p.read_text(encoding='utf-8')),
        sha=sha, acrescentar=acrescentar, NOMES=('AR', 'F', 'G'))
    monkeypatch.setattr(modulo, 'RAIZ', tmp_path)
    monkeypatch.setitem(sys.modules, 'avaliacao', avaliacao_falsa)
    monkeypatch.setitem(sys.modules, 'deepeval.config.settings', SimpleNamespace(get_settings=lambda:
        SimpleNamespace(DEEPEVAL_PER_TASK_TIMEOUT_SECONDS=1200, DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS=1199)))
    rodada = modulo.abrir_recuperacao('baseline')
    assert rodada.notas == {('01', 'AR'): notas[0], ('01', 'F'): notas[1]}
    assert rodada.indices_recuperacao == [0]
    with pytest.raises(ValueError, match='parcial'):
        modulo.abrir_recuperacao('baseline')
    nova = modulo.abrir_recuperacao('baseline', retomar=True)
    assert nova.notas == rodada.notas
    assert len(nova.log.read_text(encoding='utf-8').splitlines()) == 3
    assert sha(original) == antes
