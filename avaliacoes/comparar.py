"""Consolida métricas existentes; não faz chamadas à AWS nem ao juiz."""
import csv
from datetime import datetime, timezone
from pathlib import Path
from campanha import RAIZ, ler, sha, gravar
from resultados_validos import resolver_b


def main():
    linhas, fontes = [], {}
    for tipo in ('golden', 'redteam'):
        for versao in ('baseline', 'final'):
            for frente in ('a', 'b'):
                prefixo = 'avaliacao_' if frente == 'a' else ''
                path = RAIZ / f'resultados/frente_{frente}/{prefixo}{tipo}_{versao}.json'
                if frente == 'b':
                    path = resolver_b(path)
                dados = ler(path)
                status = dados.get('status') or dados.get('metadata', {}).get('status')
                if status != 'finalizado':
                    raise ValueError(f'Rodada incompleta ou com erro técnico: {path}')
                fontes[str(path.relative_to(RAIZ))] = sha(path)
                if frente == 'b':
                    if dados['log_sha256'] != sha(path.with_suffix('.jsonl')):
                        raise ValueError('JSONL DeepEval mudou desde a conclusão.')
                    for nome, resumo in dados['resumo'].items():
                        linhas.append({'frente': frente, 'tipo': tipo, 'versao': versao, 'metrica': nome,
                                       'unidade': 'casos', **resumo})
                else:
                    nomes = dados['avaliadores']
                    for nome in nomes:
                        notas = [n for r in dados['resultados'] for n in r.get('resposta_aws', {}).get('evaluationResults', []) if n.get('evaluatorId') == nome]
                        validas = [n for n in notas if isinstance(n.get('value'), (int, float)) and not n.get('errorCode')]
                        erros = sum(bool(r.get('erro')) for r in dados['resultados'] if r.get('evaluatorId') == nome) + sum(bool(n.get('errorCode')) for n in notas)
                        linhas.append({'frente': frente, 'tipo': tipo, 'versao': versao, 'metrica': nome,
                            'unidade': 'notas AWS; podem exceder sessões', 'avaliados': len(validas),
                            'aprovados': sum(n.get('label') == 'PASS' for n in validas) if not nome.startswith('Builtin.') else '',
                            'erros': erros, 'nao_avaliaveis': len(notas) - len(validas),
                            'media': sum(n['value'] for n in validas) / len(validas) if validas else None})
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destino = RAIZ / f'resultados/revisao/comparacao_{stamp}'
    gravar(destino.with_suffix('.json'), {'fontes_sha256': fontes, 'metricas': linhas,
        'limites': ['Médias AWS e DeepEval usam unidades distintas.',
                   'Não transformar reprovações métricas em vulnerabilidades automaticamente.',
                   'Ausência de contexto não é aprovação nem nota zero.',
                   'Revisão humana dos ataques e decisão de produção continuam necessárias.']})
    with destino.with_suffix('.csv').open('x', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(linhas[0]))
        writer.writeheader()
        writer.writerows(linhas)
    print('Comparação salva:', destino.with_suffix('.csv'))


if __name__ == '__main__':
    main()
