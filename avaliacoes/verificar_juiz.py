"""Carrega o juiz local sem perguntas, notas ou chamadas à AWS."""
from datetime import datetime, timezone
import json
from pathlib import Path

from ollama import Client
from avaliacao import juizes_instalados
from src.deepeval.juiz import JUIZ_PADRAO, OPCOES_JUIZ


def main():
    digests = juizes_instalados()
    cliente = Client(timeout=300)
    print('Carregando o juiz com 16.384 tokens; aguarde...', flush=True)
    cliente.chat(model=JUIZ_PADRAO, messages=[], options=dict(OPCOES_JUIZ), keep_alive='10m')
    ativos = [m.model_dump(mode='json') for m in cliente.ps().models]
    juiz = next((m for m in ativos if m.get('digest') == digests[JUIZ_PADRAO]), None)
    if juiz is None:
        raise RuntimeError('O juiz esperado não apareceu entre os modelos carregados.')
    pasta = Path(__file__).resolve().parent / 'resultados/revisao'
    pasta.mkdir(parents=True, exist_ok=True)
    agora = datetime.now(timezone.utc)
    arquivo = pasta / f'juiz_contexto_{agora:%Y%m%dT%H%M%S%fZ}.json'
    with arquivo.open('x', encoding='utf-8') as destino:
        json.dump({'data_utc': agora.isoformat(), 'opcoes_solicitadas': OPCOES_JUIZ,
                   'digests': digests, 'modelo_carregado': juiz,
                   'limite': 'Verifica carregamento; não avalia respostas nem garante que todo prompt caiba.'},
                  destino, ensure_ascii=False, indent=2)
    print(json.dumps(juiz, ensure_ascii=False, indent=2))
    print(f'Diagnóstico salvo: {arquivo}')
    if juiz.get('context_length') != OPCOES_JUIZ['num_ctx']:
        raise RuntimeError('Contexto efetivo ausente ou diferente do solicitado; conferir antes da suíte.')
    print('Contexto de 16.384 tokens confirmado. Nenhuma avaliação foi executada.')


if __name__ == '__main__':
    main()
