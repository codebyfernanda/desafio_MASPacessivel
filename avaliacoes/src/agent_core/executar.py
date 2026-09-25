# Estudo: nomes claros, responsabilidades explícitas e comentários sobre decisões.
# Cada chamada avalia uma sessão. Erros e resultados brutos são preservados
# para que ausência de evidência nunca seja contabilizada como aprovação.

"""Avalia spans reais com os integrados, só o customizado ou os três avaliadores."""
import argparse, hashlib, json, time
from datetime import datetime, timezone
from pathlib import Path

def separar_sessoes(spans):
    grupos = {}
    for span in spans:
        atributos_span = span.get('attributes', {})
        sessao = atributos_span.get('session.id') or atributos_span.get('gen_ai.conversation.id') or atributos_span.get('session', {}).get('id')
        if not sessao:
            raise ValueError('Span sem identificador de sessão suportado; valide o formato de telemetria antes de enviar.')
        grupos.setdefault(sessao, []).append(span)
    return grupos


def salvar_resultado(caminho, resultado):
    """Repete somente a gravação quando o Windows bloqueia a troca do arquivo."""
    temporario = caminho.with_suffix('.tmp')
    temporario.write_text(json.dumps(resultado, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    for tentativa in range(5):
        try:
            temporario.replace(caminho)
            return
        except PermissionError:
            if tentativa == 4:
                raise PermissionError(f'Gravação bloqueada. Resultados preservados em {temporario}. Use --retomar após liberar o arquivo.')
            time.sleep(0.2 * (2 ** tentativa))


def carregar_retomada(caminho, esperado, pares_previstos):
    """Recupera o temporário somente se ele prolonga os mesmos resultados salvos."""
    fontes = [p for p in (caminho, caminho.with_suffix('.tmp')) if p.is_file()]
    if not fontes:
        raise ValueError('Não há JSON ou temporário para retomar.')
    candidatos = []
    proveniencia = []
    for fonte in fontes:
        bruto = fonte.read_bytes()
        dados = json.loads(bruto.decode('utf-8-sig'))
        if dados.get('status') not in ('em_execucao', 'finalizado', 'finalizado_com_erros'):
            raise ValueError('Retome somente uma avaliação interrompida em_execucao.')
        for campo in ('versao', 'region', 'spans_sha256', 'avaliadores', 'sessoes_previstas', 'customizado_pendente', 'integrados_nesta_execucao'):
            if dados.get(campo) != esperado.get(campo):
                raise ValueError(f'Retomada recusada: {campo} mudou.')
        registros = dados.get('resultados')
        if not isinstance(registros, list) or len(registros) > len(pares_previstos):
            raise ValueError('Lista de resultados inválida ou excedente.')
        pares = [(r.get('sessionId'), r.get('evaluatorId')) for r in registros]
        if pares != pares_previstos[:len(pares)]:
            raise ValueError('Sessões ou avaliadores repetidos, fora de ordem ou diferentes da captura.')
        if dados['status'] != 'em_execucao' and len(pares) != len(pares_previstos):
            raise ValueError('Arquivo encerrado sem todos os resultados previstos.')
        for registro in registros:
            # Erros já recebidos também são preservados, nunca repetidos para melhorar a nota.
            if not registro.get('erro') and not registro.get('resposta_aws', {}).get('evaluationResults'):
                raise ValueError('Resultado incompleto; confira a evidência antes de repetir uma chamada.')
        candidatos.append(dados)
        proveniencia.append({'arquivo': str(fonte), 'sha256': hashlib.sha256(bruto).hexdigest(), 'resultados': len(registros)})
    if len(candidatos) == 2:
        primeiro, segundo = candidatos
        variaveis = {'resultados', 'retomadas', 'status', 'fim'}
        if {k: v for k, v in primeiro.items() if k not in variaveis} != {k: v for k, v in segundo.items() if k not in variaveis}:
            raise ValueError('JSON e temporário possuem metadados divergentes; preserve ambos.')
        menor, maior = sorted(candidatos, key=lambda d: len(d['resultados']))
        if maior['resultados'][:len(menor['resultados'])] != menor['resultados']:
            raise ValueError('JSON e temporário possuem resultados divergentes; preserve ambos.')
        historicos = sorted((d.get('retomadas', []) for d in candidatos), key=len)
        if historicos[1][:len(historicos[0])] != historicos[0]:
            raise ValueError('Históricos de retomada divergentes; preserve ambos.')
    resultado = max(candidatos, key=lambda d: len(d['resultados']))
    resultado['retomadas'] = list(max((d.get('retomadas', []) for d in candidatos), key=len))
    resultado['status'] = 'em_execucao'
    resultado.setdefault('retomadas', []).append({
        'data': datetime.now(timezone.utc).isoformat(), 'fontes': proveniencia,
        'resultados_preservados': len(resultado['resultados']),
    })
    return resultado

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spans', type=Path, required=True)
    modo = p.add_mutually_exclusive_group(required=True)
    modo.add_argument('--custom-id', help='Executa os dois integrados e este avaliador customizado.')
    modo.add_argument('--somente-integrados', action='store_true', help='Executa Helpfulness e Faithfulness; mantém o customizado pendente.')
    modo.add_argument('--somente-customizado', metavar='ID', help='Executa apenas este customizado, sem repetir os integrados.')
    p.add_argument('--versao', choices=['baseline', 'final'], required=True)
    p.add_argument('--saida', type=Path, required=True)
    p.add_argument('--profile')
    p.add_argument('--region', default='sa-east-1')
    p.add_argument('--validar', action='store_true', help='Valida o arquivo sem chamar a AWS; não gera notas.')
    p.add_argument('--retomar', action='store_true', help='Continua uma avaliação interrompida, preservando o JSON e seu temporário compatível.')
    argumentos_cli = p.parse_args()
    if not argumentos_cli.retomar and (argumentos_cli.saida.exists() or argumentos_cli.saida.with_suffix('.tmp').exists()):
        raise SystemExit('A saída já existe; escolha outro nome para preservar a evidência.')
    dados = json.loads(argumentos_cli.spans.read_text(encoding='utf-8'))
    spans = dados.get('sessionSpans') if isinstance(dados, dict) else dados
    if not isinstance(spans, list) or not spans or (not all((isinstance(s, dict) and 'traceId' in s and ('spanId' in s) for s in spans))):
        raise SystemExit('Forneça sessionSpans reais, com traceId e spanId; uma transcrição não basta.')
    grupos = separar_sessoes(spans)
    sessoes_previstas = dados.get('metadata', {}).get('sessions') if isinstance(dados, dict) else None
    if sessoes_previstas is not None and set(sessoes_previstas) != set(grupos):
        raise SystemExit('As sessões dos spans não correspondem às sessões previstas na exportação. Não avaliar um arquivo parcial.')
    if argumentos_cli.validar:
        print(f'{len(spans)} spans de {len(grupos)} sessões estruturalmente válidos; nenhuma avaliação executada.')
        return
    avaliadores = [argumentos_cli.somente_customizado] if argumentos_cli.somente_customizado else ['Builtin.Helpfulness', 'Builtin.Faithfulness']
    if argumentos_cli.custom_id:
        avaliadores.append(argumentos_cli.custom_id)
    resultado = {
        'versao': argumentos_cli.versao,
        'region': argumentos_cli.region,
        'origem_spans': str(argumentos_cli.spans),
        'spans_sha256': hashlib.sha256(argumentos_cli.spans.read_bytes()).hexdigest(),
        'avaliadores': avaliadores,
        'customizado_pendente': argumentos_cli.somente_integrados,
        'integrados_nesta_execucao': not bool(argumentos_cli.somente_customizado),
        'sessoes_previstas': len(grupos),
        'inicio': datetime.now(timezone.utc).isoformat(),
        'status': 'em_execucao',
        'resultados': [],
    }
    argumentos_cli.saida.parent.mkdir(parents=True, exist_ok=True)
    pares_previstos = [(sessao, avaliador) for sessao in grupos for avaliador in avaliadores]
    if argumentos_cli.retomar:
        resultado = carregar_retomada(argumentos_cli.saida, resultado, pares_previstos)
        print(f"Retomada: {len(resultado['resultados'])} avaliações preservadas; {len(pares_previstos) - len(resultado['resultados'])} pendentes.", flush=True)
    concluidos = {(r['sessionId'], r['evaluatorId']) for r in resultado['resultados']}

    def salvar():
        salvar_resultado(argumentos_cli.saida, resultado)

    salvar()
    import boto3
    from botocore.config import Config
    cliente_servico = boto3.Session(profile_name=argumentos_cli.profile, region_name=argumentos_cli.region).client('bedrock-agentcore', config=Config(read_timeout=300))
    for numero, (session_id, spans_da_sessao) in enumerate(grupos.items(), start=1):
        for identificador_avaliador in avaliadores:
            if (session_id, identificador_avaliador) in concluidos:
                continue
            print(f'Sessão {numero}/{len(grupos)}: executando {identificador_avaliador}...', flush=True)
            try:
                resposta_servico = cliente_servico.evaluate(evaluatorId=identificador_avaliador, evaluationInput={'sessionSpans': spans_da_sessao})
                if not resposta_servico.get('evaluationResults'):
                    raise ValueError('AWS não retornou resultados de avaliação.')
                resultado['resultados'].append({'sessionId': session_id, 'evaluatorId': identificador_avaliador, 'resposta_aws': resposta_servico})
                situacao = 'retorno com erro' if any(x.get('errorCode') for x in resposta_servico['evaluationResults']) else 'resultado recebido'
            except Exception as erro_execucao:
                resultado['resultados'].append({'sessionId': session_id, 'evaluatorId': identificador_avaliador, 'erro': f'{type(erro_execucao).__name__}: {erro_execucao}'})
                situacao = 'erro registrado'
            salvar()
            # Receber uma nota não significa aprovação: a análise usa o retorno bruto.
            print(f'Sessão {numero}/{len(grupos)}: {identificador_avaliador} — {situacao}.', flush=True)
    tem_erros = any((r.get('erro') or any((x.get('errorCode') for x in r.get('resposta_aws', {}).get('evaluationResults', []))) for r in resultado['resultados']))
    resultado['status'] = 'finalizado_com_erros' if tem_erros else 'finalizado'
    resultado['fim'] = datetime.now(timezone.utc).isoformat()
    salvar()
    if tem_erros:
        raise SystemExit('Há erros na avaliação; consulte o relatório, sem contabilizá-los como aprovação.')
    print(f'Avaliação concluída: {len(grupos)} sessões, {len(avaliadores)} avaliadores. Arquivo: {argumentos_cli.saida}', flush=True)
    if argumentos_cli.somente_integrados:
        print('O avaliador customizado continua pendente; esta execução contém somente os dois integrados.')
    if argumentos_cli.somente_customizado:
        print('Esta execução contém somente o customizado. Os resultados dos integrados permanecem nos arquivos anteriores.')
if __name__ == '__main__':
    main()
