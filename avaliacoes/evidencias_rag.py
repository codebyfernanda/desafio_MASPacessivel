"""Leitor de eventos estruturados; não faz chamadas de rede."""
import json
import hashlib
TOOL = "base-masp___RAG_MASP"
SOURCE = "s3://masp-rag-base-conhecimento-fernandab-024687770728-sa-east-1-an/masp_base_conhecimento.txt"

def objects(value):
    """Percorre somente resultados estruturados da ferramenta, inclusive JSON textual."""
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from objects(item)
    elif isinstance(value, list):
        for item in value:
            yield from objects(item)
    elif isinstance(value, str) and value.lstrip().startswith(('{', '[')):
        try:
            parsed = json.loads(value)
        except (ValueError, RecursionError):
            return
        yield from objects(parsed)


def summarize(events):
    calls, results, blocks = {}, {}, {}
    last_stop = None
    final_answers, message_text, errors = [], [], []
    for event in events:
        for key in event:
            if key.endswith(('Exception', 'Error')):
                errors.append({key: event[key]})
        if 'messageStart' in event:
            blocks = {}
            message_text = []
        e = event.get('contentBlockStart', {})
        start = e.get('start', {})
        index = e.get('contentBlockIndex')
        if 'toolUse' in start:
            c = dict(start['toolUse'])
            c['input_fragmentos'] = ''
            cid = c['toolUseId']
            calls[cid] = c
            blocks[index] = ('call', cid)
        if 'toolResult' in start:
            r = dict(start['toolResult'])
            r['conteudo'] = []
            rid = r['toolUseId']
            results[rid] = r
            blocks[index] = ('result', rid)
        e = event.get('contentBlockDelta', {})
        d = e.get('delta', {})
        ref = blocks.get(e.get('contentBlockIndex'))
        if isinstance(d.get('text'), str):
            message_text.append(d['text'])
        if ref and ref[0] == 'call':
            calls[ref[1]]['input_fragmentos'] += d.get('toolUse', {}).get('input', '')
        if ref and ref[0] == 'result':
            results[ref[1]]['conteudo'].extend(d.get('toolResult', []))
        if 'messageStop' in event:
            last_stop = event['messageStop'].get('stopReason')
            if last_stop == 'end_turn':
                final_answers.append(''.join(message_text).strip())
    evidence = []
    for cid, call in calls.items():
        # Texto que apenas menciona tool_code/tools/call nunca entra nesta lista.
        if call.get('name') not in (TOOL, '@masp-rag/' + TOOL):
            continue
        result = results.get(cid, {})
        docs = []
        content = result.get('conteudo', [])
        text_parts = ''.join(x.get('text', '') for x in content if isinstance(x, dict))
        for obj in objects([content, text_parts]):
            body = obj.get('conteudo')
            digest = obj.get('sha256')
            if obj.get('fonte') != SOURCE or not isinstance(body, str) or not body.strip():
                continue
            hashes = [hashlib.sha256(body.encode(enc)).hexdigest() for enc in ('utf-8','utf-8-sig')]
            docs.append({'fonte': SOURCE, 'sha256_retornado': digest,
                         'hash_conteudo_confere': digest in hashes,
                         'caracteres': len(body), 'conteudo': body})
        evidence.append({'toolUseId': cid, 'name': call.get('name'),
                         'serverName': call.get('serverName'),
                         'argumentos': call.get('input_fragmentos'),
                         'status_retorno': result.get('status'), 'documentos': docs})
    observed = any(x['status_retorno'] == 'success' and
                   any(d['hash_conteudo_confere'] for d in x['documentos']) for x in evidence)
    return {'chamadas_estruturadas_rag': evidence, 'todos_nomes_solicitados': [x.get('name') for x in calls.values()],
            'solicitacao_e_retorno_rag_observados': observed,
            'resposta_final': final_answers[-1] if final_answers else None,
            'stop_reason': last_stop, 'erros_stream': errors,
            'limite': 'O retorno correlacionado sustenta a chamada real neste experimento; uso correto dos fatos na resposta requer revisão. Ausência no stream requer conferir spans; não prova incapacidade do modelo. Não é aprovação da campanha nem publicação de nova configuração.'}

