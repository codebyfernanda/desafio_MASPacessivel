"""Última rodada: 35 casos e 15 ataques, duas frentes e comparação."""
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone
from campanha import RAIZ, ler, gravar, sha, validar_comparabilidade, configuracao
from resultados_validos import resolver_b


def concluido(path):
    if not path.exists():
        return False
    dados = ler(path)
    estado = dados.get('status') or dados.get('metadata', {}).get('status')
    if estado != 'finalizado':
        raise ValueError(f'Arquivo encerrado com pendência técnica: {path}. Não será repetido automaticamente.')
    if any(n.get('erro') or n.get('status') == 'erro' or
           any(v.get('errorCode') for v in n.get('resposta_aws', {}).get('evaluationResults', []))
           for n in dados.get('resultados', [])):
        raise ValueError(f'Resultados contêm erro técnico: {path}')
    return True


def executar(etapa, tipo, path):
    if concluido(path):
        print(f'{etapa} {tipo}: já concluído; preservado.', flush=True)
        return
    args = [sys.executable, 'campanha.py', etapa, tipo, 'final']
    if etapa == 'capturar' and path.with_suffix('.jsonl').exists():
        args.append('--retomar')
    # Não retoma avaliações AWS automaticamente: a saída parcial pode ter outro formato.
    if subprocess.call(args, cwd=RAIZ) != 0 or not path.exists():
        raise RuntimeError(f'Etapa {etapa} {tipo} interrompida. Preserve arquivos e envie a saída.')
    concluido(path)


def main():
    # Verifica os baselines antes de gerar qualquer custo novo.
    for tipo in ('golden', 'redteam'):
        for path in (RAIZ / f'resultados/frente_a/avaliacao_{tipo}_baseline.json',
                     resolver_b(RAIZ / f'resultados/frente_b/{tipo}_baseline.json')):
            if not concluido(path):
                raise ValueError('Baseline ausente: ' + str(path))
        validar_comparabilidade(tipo, 'final', configuracao('final')) if tipo == 'golden' else None
    print('Última rodada: novas chamadas AWS para 35 casos e 15 ataques; DeepEval local. Baselines preservados.', flush=True)
    for tipo in ('golden', 'redteam'):
        executar('capturar', tipo, RAIZ / f'resultados/frente_a/{tipo}_final.json')
        spans = RAIZ / f'resultados/frente_a/spans_{tipo}_final.json'
        if not spans.exists():
            # Repetir consulta de logs não repete invocações do agente.
            for tentativa in range(5):
                if subprocess.call([sys.executable, 'campanha.py', 'spans', tipo, 'final'], cwd=RAIZ) == 0 and spans.exists():
                    break
                if tentativa == 4:
                    raise RuntimeError('Spans ainda indisponíveis. Envie a saída; não repetir capturas.')
                print('Aguardando 45 segundos pela ingestão dos spans...', flush=True)
                time.sleep(45)
        executar('avaliar-a', tipo, RAIZ / f'resultados/frente_a/avaliacao_{tipo}_final.json')
    for tipo in ('golden', 'redteam'):
        path = RAIZ / f'resultados/frente_b/{tipo}_final.json'
        if path.exists() and ler(path)['metadata']['status'] == 'finalizado_com_erros':
            derivado = path.with_name(path.stem + '_recuperacao.json')
            if not derivado.exists():
                from recuperar_deepeval import selecionar_timeouts
                selecionar_timeouts(ler(path))
                args = [sys.executable, 'recuperar_deepeval.py', tipo, 'final']
                if derivado.with_suffix('.jsonl').exists():
                    args.append('--retomar')
                subprocess.call(args, cwd=RAIZ)
            if not derivado.exists():
                raise RuntimeError('Recuperação interrompida; preserve os registros e envie a saída.')
        if concluido(resolver_b(path)):
            print(f'DeepEval {tipo}: já concluído; preservado.', flush=True)
            continue
        ambiente = os.environ.copy()
        ambiente.update(MASP_QWEN_TIPO=tipo, MASP_QWEN_VERSAO='final',
                        MASP_QWEN_RETOMAR='1' if path.with_suffix('.jsonl').exists() else '0',
                        DEEPEVAL_PER_TASK_TIMEOUT_SECONDS_OVERRIDE='1200',
                        DEEPEVAL_RETRY_MAX_ATTEMPTS='1', DEEPEVAL_DISABLE_TIMEOUTS='false',
                        DEEPEVAL_TELEMETRY_OPT_OUT='YES', PYTHONIOENCODING='utf-8')
        for key in ('DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS_OVERRIDE', 'DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS', 'DEEPEVAL_PER_TASK_TIMEOUT_SECONDS'):
            ambiente.pop(key, None)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        gravar(RAIZ / f'resultados/revisao/execucao_final_{tipo}_{stamp}.json',
               {'timeout_metrica': 1200, 'tentativas_deepeval': 1,
                'codigo_executor_sha256': sha(Path(__file__)), 'tipo': tipo, 'versao': 'final'})
        cli = Path(sys.executable).with_name('deepeval.exe' if os.name == 'nt' else 'deepeval')
        subprocess.call([str(cli), 'test', 'run', 'test_qwen.py', '-v'], cwd=RAIZ, env=ambiente)
        # Pytest pode retornar 1 por notas baixas; isso é evidência, não falha técnica.
        if not concluido(path):
            raise RuntimeError('DeepEval interrompido. Envie a saída antes de continuar.')
    if subprocess.call([sys.executable, 'comparar.py'], cwd=RAIZ):
        raise RuntimeError('Comparação não concluída; preserve todos os resultados.')
    print('RODADA FINAL CONCLUÍDA. Comparação salva em resultados/revisao. Próximo: revisar achados finais e fechar relatório/ZIP.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError) as erro:
        print(str(erro), file=sys.stderr)
        sys.exit(1)
