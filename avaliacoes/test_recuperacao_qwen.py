"""Execução via DeepEval/pytest de timeouts, sem repetir notas válidas."""
import os
import pytest
from recuperar_deepeval import abrir_recuperacao

pytestmark = pytest.mark.skipif(os.getenv('MASP_QWEN_RECUPERAR') != '1',
                               reason='Execute recuperar_deepeval.py para a recuperação técnica.')


@pytest.fixture(scope='session')
def recuperacao():
    trabalho = abrir_recuperacao(os.environ['MASP_QWEN_VERSAO'],
                                os.getenv('MASP_QWEN_RETOMAR') == '1')
    yield trabalho
    trabalho.encerrar()


@pytest.mark.parametrize('indice', range(35 if os.getenv('MASP_QWEN_TIPO', 'golden') == 'golden' else 15))
def test_recuperacao(recuperacao, indice):
    if indice not in recuperacao.indices_recuperacao:
        pytest.skip('Caso sem timeout; resultado original preservado.')
    notas = recuperacao.avaliar(indice)
    alvos = {tuple(k) for k in recuperacao.meta['recuperacao_tecnica']['alvos']}
    novas = [n for n in notas if (n['caso_id'], n['metrica']) in alvos]
    assert not any(n['status'] == 'erro' or n['passou'] is False for n in novas), \
        'Recuperação com erro ou nota abaixo do corte; consulte o novo JSONL.'
