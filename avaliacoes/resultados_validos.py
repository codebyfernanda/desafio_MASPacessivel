"""Seleciona a recuperação técnica sem apagar nem ocultar a origem."""
from campanha import ler, sha


def resolver_b(original):
    recuperado = original.with_name(original.stem + '_recuperacao.json')
    if not recuperado.exists():
        return original
    origem, novo = ler(original), ler(recuperado)
    meta = novo['metadata']['recuperacao_tecnica']
    if meta['origem_sha256'] != sha(original):
        raise ValueError('Origem da recuperação foi alterada.')
    for path, dados in ((original, origem), (recuperado, novo)):
        if dados['log_sha256'] != sha(path.with_suffix('.jsonl')):
            raise ValueError('JSONL divergente: ' + str(path))
    antes = {(n['caso_id'], n['metrica']): n for n in origem['resultados']}
    depois = {(n['caso_id'], n['metrica']): n for n in novo['resultados']}
    if len(depois) != len(novo['resultados']) or antes.keys() != depois.keys():
        raise ValueError('Recuperação com casos divergentes.')
    for chave, nota in antes.items():
        if nota['status'] != 'erro' and depois[chave] != nota:
            raise ValueError('Resultado válido foi modificado na recuperação.')
    for campo, valor in origem['metadata'].items():
        if campo not in ('status', 'limites', 'harness') and novo['metadata'].get(campo) != valor:
            raise ValueError('Protocolo da recuperação diverge em ' + campo)
    return recuperado
