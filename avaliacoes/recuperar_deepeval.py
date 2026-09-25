"""Recupera somente timeouts de uma rodada encerrada, preservando o original."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

RAIZ = Path(__file__).resolve().parent


def selecionar_timeouts(dados):
    notas = dados['resultados']
    chaves = [(n['caso_id'], n['metrica']) for n in notas]
    if len(chaves) != len(set(chaves)):
        raise ValueError('Resultados duplicados na origem.')
    erros = [n for n in notas if n['status'] == 'erro']
    if not erros or any(not any(t in n.get('erro', '') for t in ('TimeoutError', 'ReadTimeout')) for n in erros):
        raise ValueError('Esta recuperação exige erros de timeout; investigar outros erros separadamente.')
    return {(n['caso_id'], n['metrica']) for n in erros}


def abrir_recuperacao(versao, retomar=False):
    from avaliacao import Rodada, TIPO, carregar, assinatura, ler, sha, acrescentar, NOMES
    # Inicialização própria: Rodada normalmente recusa reabrir um resultado final.
    # Reutilizamos somente sua avaliação e gravação, em novos arquivos.
    trabalho = Rodada.__new__(Rodada)
    trabalho.origem, trabalho.captura, trabalho.golden = carregar(versao)
    trabalho.pasta = RAIZ / 'resultados/frente_b'
    original = trabalho.pasta / f'{TIPO}_{versao}.json'
    dados = ler(original)
    if dados['metadata']['status'] != 'finalizado_com_erros':
        raise ValueError('A origem deve estar encerrada com erros técnicos.')
    if dados['log_sha256'] != sha(original.with_suffix('.jsonl')):
        raise ValueError('O JSONL original mudou desde a conclusão.')
    atual = assinatura(versao, trabalho.origem)
    for campo, valor in atual.items():
        if dados['metadata'].get(campo) != valor:
            raise ValueError(f'O protocolo mudou em {campo}. Não recuperar misturando configurações.')
    alvos = selecionar_timeouts(dados)
    esperadas = {(c['id'], nome) for c in trabalho.golden for nome in NOMES}
    recebidas = {(n['caso_id'], n['metrica']) for n in dados['resultados']}
    if recebidas != esperadas:
        raise ValueError('A origem não contém todos os casos e métricas esperados.')
    from deepeval.config.settings import get_settings
    settings = get_settings()
    trabalho.meta = {**atual, 'recuperacao_tecnica': {
        'origem': original.relative_to(RAIZ).as_posix(),
        'origem_sha256': sha(original), 'log_original_sha256': dados['log_sha256'],
        'motivo': 'Timeouts na rodada original; apenas erros técnicos são repetidos com maior prazo.',
        'alvos': [list(k) for k in sorted(alvos)],
        'codigo_recuperacao_sha256': {n: sha(RAIZ / n) for n in ('recuperar_deepeval.py', 'test_recuperacao_qwen.py')},
        'timeout_metrica_segundos': settings.DEEPEVAL_PER_TASK_TIMEOUT_SECONDS,
        'timeout_tentativa_segundos': settings.DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS,
        'timeout_http_ollama_segundos': 300,
        'limite': 'Nova tentativa técnica. Notas válidas, inclusive reprovações, e não avaliáveis são preservados. Não é nova captura do agente.'}}
    trabalho.log = trabalho.pasta / f'{TIPO}_{versao}_recuperacao.jsonl'
    trabalho.saida = trabalho.log.with_suffix('.json')
    if trabalho.saida.exists():
        raise ValueError('Recuperação já encerrada. Preserve o resultado; não repetir para melhorar notas.')
    preservadas = {(n['caso_id'], n['metrica']): n for n in dados['resultados']
                   if (n['caso_id'], n['metrica']) not in alvos}
    if trabalho.log.exists():
        if not retomar:
            raise ValueError('Recuperação parcial existente; use --retomar.')
        linhas = [json.loads(l) for l in trabalho.log.read_text(encoding='utf-8').splitlines()]
        if not linhas or linhas[0] != {'metadata': trabalho.meta}:
            raise ValueError('Metadados divergentes; retomada recusada.')
        trabalho.notas = {}
        for n in linhas[1:]:
            chave = (n['caso_id'], n['metrica'])
            if chave not in esperadas or chave in trabalho.notas:
                raise ValueError('Log de recuperação inválido.')
            if chave in preservadas and n != preservadas[chave]:
                raise ValueError('Uma nota válida original foi alterada.')
            trabalho.notas[chave] = n
    else:
        with trabalho.log.open('x', encoding='utf-8') as f:
            f.write(json.dumps({'metadata': trabalho.meta}, ensure_ascii=False) + '\n')
        trabalho.notas = {}
    # Retomada também completa uma interrupção durante a cópia inicial.
    for chave, nota in preservadas.items():
        if chave not in trabalho.notas:
            acrescentar(trabalho.log, nota)
            trabalho.notas[chave] = nota
    trabalho.indices_recuperacao = [i for i, c in enumerate(trabalho.golden)
                                   if any(c['id'] == caso for caso, _ in alvos)]
    print(f'{len(alvos)} avaliações com timeout selecionadas; {len(preservadas)} registros originais preservados.', flush=True)
    return trabalho


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tipo', choices=('golden', 'redteam'))
    parser.add_argument('versao', choices=('baseline', 'final'))
    parser.add_argument('--retomar', action='store_true')
    args = parser.parse_args()
    ambiente = os.environ.copy()
    ambiente.update(MASP_QWEN_TIPO=args.tipo, MASP_QWEN_VERSAO=args.versao,
                    MASP_QWEN_RECUPERAR='1', MASP_QWEN_RETOMAR='1' if args.retomar else '0',
                    DEEPEVAL_PER_TASK_TIMEOUT_SECONDS_OVERRIDE='1200',
                    DEEPEVAL_RETRY_MAX_ATTEMPTS='1', DEEPEVAL_DISABLE_TIMEOUTS='false',
                    DEEPEVAL_TELEMETRY_OPT_OUT='YES', PYTHONIOENCODING='utf-8')
    ambiente.pop('DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS_OVERRIDE', None)
    ambiente.pop('DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS', None)
    ambiente.pop('DEEPEVAL_PER_TASK_TIMEOUT_SECONDS', None)
    comando = Path(sys.executable).with_name('deepeval.exe' if os.name == 'nt' else 'deepeval')
    if not comando.exists():
        raise FileNotFoundError('Execute com o Python da .venv que contém DeepEval.')
    print('Recuperação local: 1.200s por métrica; nenhuma chamada à AWS. Originais preservados.', flush=True)
    return subprocess.call([str(comando), 'test', 'run', 'test_recuperacao_qwen.py', '-v'],
                           cwd=RAIZ, env=ambiente)


if __name__ == '__main__':
    sys.exit(main())
