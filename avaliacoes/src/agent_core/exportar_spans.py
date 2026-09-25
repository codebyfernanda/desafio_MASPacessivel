# Estudo: nomes claros, responsabilidades explícitas e comentários sobre decisões.
# A consulta limita-se às sessões de teste indicadas. Rejeitar uma saída
# truncada evita avaliar silenciosamente apenas parte da conversa.

"""Exporta somente sessões de teste indicadas, via CloudWatch Logs Insights."""
import argparse, json, re, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

def ler_sessoes_capturadas(caminho):
    """Lê os IDs da captura sem enviar perguntas ou respostas ao CloudWatch."""
    captura = json.loads(caminho.read_text(encoding='utf-8-sig'))
    if not isinstance(captura, dict) or captura.get('metadata', {}).get('status') != 'finalizado':
        raise ValueError('Use uma captura finalizada, sem erros.')
    resultados = captura.get('resultados')
    if not isinstance(resultados, list) or not resultados:
        raise ValueError('A captura não contém casos para exportar.')
    sessoes = []
    for caso in resultados:
        if not isinstance(caso, dict) or caso.get('erro') or not caso.get('session_id'):
            raise ValueError('Há um caso com erro ou sem session_id na captura.')
        sessoes.append(caso['session_id'])
    if not all(isinstance(sessao, str) for sessao in sessoes) or len(set(sessoes)) != len(sessoes):
        raise ValueError('Os IDs de sessão da captura devem ser textos únicos por caso.')
    return sessoes

def main():
    p = argparse.ArgumentParser(description=__doc__)
    origem = p.add_mutually_exclusive_group(required=True)
    origem.add_argument('--session-id', action='append')
    origem.add_argument('--captura', type=Path, help='Captura JSON: exporta automaticamente todas as sessões.')
    p.add_argument('--log-group', action='append', required=True)
    p.add_argument('--region', default='sa-east-1')
    p.add_argument('--profile')
    p.add_argument('--horas', type=int, default=2)
    p.add_argument('--saida', type=Path, required=True)
    a = p.parse_args()
    if a.captura:
        try:
            a.session_id = ler_sessoes_capturadas(a.captura)
        except (OSError, ValueError) as erro:
            p.error(str(erro))
    if a.saida.exists():
        raise SystemExit('O arquivo já existe; não sobrescreva evidências.')
    if not 1 <= a.horas <= 24:
        raise SystemExit('Use intervalo de 1 a 24 horas.')
    if not all((re.fullmatch('[A-Za-z0-9_.:/-]{1,200}', s) for s in a.session_id)):
        raise SystemExit('Identificador de sessão inválido para esta consulta.')
    import boto3
    cliente_servico = boto3.Session(profile_name=a.profile, region_name=a.region).client('logs')
    fim = datetime.now(timezone.utc)
    inicio = fim - timedelta(hours=a.horas)
    spans = []
    sessoes_ausentes = []
    for numero, session in enumerate(a.session_id, start=1):
        total_anterior = len(spans)
        consulta_logs = 'fields @timestamp, @message | filter ispresent(scope.name) and attributes.session.id = ' + json.dumps(session) + ' | sort @timestamp asc | limit 10000'
        resposta_servico = cliente_servico.start_query(logGroupNames=a.log_group, startTime=int(inicio.timestamp()), endTime=int(fim.timestamp()), queryString=consulta_logs)
        limite = time.monotonic() + 120
        while True:
            resultado = cliente_servico.get_query_results(queryId=resposta_servico['queryId'])
            status = resultado['status']
            if status == 'Complete':
                break
            if status not in ('Scheduled', 'Running'):
                raise RuntimeError(f'Consulta terminou com {status}')
            if time.monotonic() > limite:
                raise TimeoutError('Consulta ainda pendente; não foi tratada como ausência de spans.')
            time.sleep(1)
        if len(resultado['results']) >= 10000:
            raise RuntimeError('Limite de registros atingido; divida a consulta para evitar exportação incompleta.')
        for linha_resultado in resultado['results']:
            for campo_resultado in linha_resultado:
                if campo_resultado.get('field') == '@message':
                    item = json.loads(campo_resultado['value'])
                    if isinstance(item, dict) and 'traceId' in item and ('spanId' in item):
                        atributos = item.get('attributes', {})
                        sessao_encontrada = atributos.get('session.id') or atributos.get('gen_ai.conversation.id') or atributos.get('session', {}).get('id')
                        if sessao_encontrada == session:
                            spans.append(item)
        quantidade = len(spans) - total_anterior
        print(f'Sessão {numero}/{len(a.session_id)}: {quantidade} spans.', flush=True)
        if quantidade == 0:
            sessoes_ausentes.append(session)
    if not spans:
        raise SystemExit('Nenhum span encontrado; aguarde a ingestão ou confira grupos e IDs. Nenhuma avaliação foi executada.')
    # Um arquivo parcial poderia produzir uma taxa de aprovação enganosa.
    # Exigir cobertura de todas as sessões evita perder casos silenciosamente.
    if sessoes_ausentes:
        raise SystemExit(f'Exportação incompleta: {len(sessoes_ausentes)} sessões sem spans. Nenhum arquivo final foi gravado. Confira a ingestão e repita a exportação. IDs: {", ".join(sessoes_ausentes)}')
    unicos = {(s['traceId'], s['spanId']): s for s in spans}
    a.saida.parent.mkdir(parents=True, exist_ok=True)
    a.saida.write_text(json.dumps({'metadata': {'region': a.region, 'sessions': a.session_id, 'log_groups': a.log_group, 'inicio': inicio.isoformat(), 'fim': fim.isoformat(), 'origem_captura': str(a.captura) if a.captura else None}, 'sessionSpans': list(unicos.values())}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{len(unicos)} spans exportados de {len(a.session_id)} sessões.')
if __name__ == '__main__':
    main()
