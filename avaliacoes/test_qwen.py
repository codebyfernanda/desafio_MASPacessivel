"""Execute com deepeval test run test_qwen.py; usa apenas capturas salvas."""
import os
import pytest
from avaliacao import Rodada, TIPO

pytestmark = pytest.mark.skipif(
    os.getenv('MASP_QWEN_VERSAO') not in ('baseline', 'final'),
    reason='Defina MASP_QWEN_VERSAO e MASP_QWEN_TIPO conforme o roteiro.')


@pytest.fixture(scope='session')
def rodada():
    trabalho = Rodada(os.environ['MASP_QWEN_VERSAO'], os.getenv('MASP_QWEN_RETOMAR') == '1')
    yield trabalho
    trabalho.encerrar()


@pytest.mark.parametrize('indice', range(35 if TIPO == 'golden' else 15))
def test_qwen(rodada, indice):
    notas = rodada.avaliar(indice)
    falhas = [n['metrica'] for n in notas if n['status'] == 'erro' or n['passou'] is False]
    assert not falhas, f'Métricas reprovadas ou com erro: {falhas}. Consulte as justificativas no JSONL.'
    if any(n['status'] == 'nao_avaliavel' for n in notas):
        pytest.skip('Caso parcial: Faithfulness sem contexto RAG observado.')
