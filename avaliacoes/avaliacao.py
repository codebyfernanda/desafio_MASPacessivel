"""Avalia respostas AWS já salvas. Não chama a AWS nem gera novas respostas."""
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import subprocess
import sys

RAIZ = Path(__file__).resolve().parent
TIPO = os.getenv('MASP_QWEN_TIPO', 'golden')
NOMES = ('Answer Relevancy', 'Faithfulness', 'G-Eval')
MODELOS = ('MASP_JUDGE_MODEL', 'MASP_FAITHFULNESS_MODEL', 'MASP_CONFORMITY_MODEL')


def sha(arquivo):
    return hashlib.sha256(arquivo.read_bytes()).hexdigest()


def ler(arquivo):
    return json.loads(arquivo.read_text(encoding='utf-8-sig'))


def carregar(versao):
    from campanha import casos, hash_json
    from evidencias_rag import summarize
    if TIPO not in ('golden', 'redteam') or versao not in ('baseline', 'final'):
        raise ValueError('Tipo ou versão inválidos.')
    origem = RAIZ / 'resultados/frente_a' / f'{TIPO}_{versao}.json'
    captura = ler(origem)
    meta = captura['metadata']
    esperados = casos(TIPO)
    if meta.get('status') != 'finalizado' or meta.get('versao') != versao or meta.get('tipo') != TIPO:
        raise ValueError('Captura incompleta ou de outro experimento.')
    if meta.get('protocolo') != 'qwen_nativo_v1' or meta['casos_sha256'] != hash_json(esperados):
        raise ValueError('Protocolo ou dataset divergentes.')
    if meta['config_sha256'] != hash_json(meta['configuracao']):
        raise ValueError('Hash da configuração inválido.')
    if meta['configuracao']['overrides']['model']['bedrockModelConfig']['modelId'] != 'qwen.qwen3-next-80b-a3b-instruct':
        raise ValueError('A captura não pertence ao Qwen3 Next.')
    registros = captura['resultados']
    if [r['caso_id'] for r in registros] != [c['id'] for c in esperados]:
        raise ValueError('IDs ou ordem incorretos.')
    if len({r['session_id'] for r in registros}) != len(esperados):
        raise ValueError('Sessões repetidas.')
    for r, c in zip(registros, esperados, strict=True):
        if r['turnos'] != c['turnos'] or len(r['respostas']) != len(r['turnos']) or len(r['eventos_por_turno']) != len(r['turnos']):
            raise ValueError('Turnos ou respostas incompletos.')
        analises = [summarize(e) for e in r['eventos_por_turno']]
        if analises != r['analises_por_turno'] or [a['resposta_final'] for a in analises] != r['respostas']:
            raise ValueError('Evidências divergem do stream original.')
        if any(a['erros_stream'] or a['stop_reason'] != 'end_turn' for a in analises):
            raise ValueError('Há erro técnico na captura.')
    if TIPO == 'golden':
        golden = ler(RAIZ / 'dados/golden_dataset.json')
    else:
        golden = ler(RAIZ / 'dados/redteam/criterios.json')['casos']
        if [c['id'] for c in golden] != [c['id'] for c in esperados]:
            raise ValueError('Critérios defensivos não correspondem aos ataques.')
    return origem, captura, golden


def contextos(registro):
    # Somente retornos efetivamente recebidos nesta sessão. Nunca usar gabarito
    # nem consultar S3 depois da captura para preencher uma fonte ausente.
    docs = []
    for analise in registro['analises_por_turno']:
        for chamada in analise['chamadas_estruturadas_rag']:
            if chamada['status_retorno'] == 'success':
                for doc in chamada['documentos']:
                    if doc['hash_conteudo_confere'] and doc['conteudo'] not in docs:
                        docs.append(doc['conteudo'])
    return docs


def assinatura(versao, origem):
    from src.deepeval.juiz import OPCOES_JUIZ
    return {
        'protocolo': 'qwen_capturado_v1', 'tipo': TIPO, 'versao': versao,
        'captura_sha256': sha(origem), 'dataset_sha256': sha(RAIZ / ('dados/golden_dataset.json' if TIPO == 'golden' else 'dados/redteam/ataques.json')),
        'criterios_sha256': sha(RAIZ / 'dados/redteam/criterios.json'),
        'juizes': [os.getenv(k, 'deepseek-r1:latest') for k in MODELOS],
        'digests_juizes': juizes_instalados(),
        'temperatura_juiz': 0.2, 'thresholds': [0.7, 0.8, 0.8],
        'opcoes_juiz': dict(OPCOES_JUIZ),
        'codigo_sha256': {str(p.relative_to(RAIZ)): sha(p) for p in
                          [RAIZ / 'avaliacao.py', RAIZ / 'test_qwen.py', RAIZ / 'campanha.py', RAIZ / 'evidencias_rag.py', RAIZ / 'casos_captura.py']
                          + sorted((RAIZ / 'src/deepeval').glob('*.py'))},
        'bibliotecas': {n: importlib.metadata.version(n) for n in ('deepeval', 'ollama', 'pytest')},
    }


def juizes_instalados():
    """Registra o modelo real: o mesmo nome 'latest' pode mudar com um download."""
    from ollama import Client
    disponiveis = {m.model: m.digest for m in Client(timeout=10).list().models}
    escolhidos = {os.getenv(k, 'deepseek-r1:latest') for k in MODELOS}
    ausentes = escolhidos - disponiveis.keys()
    if ausentes:
        raise ValueError(f'Juiz ausente no Ollama: {sorted(ausentes)}. Confira ollama list.')
    esperado = '6995872bfe4c521a67b32da386cd21d5c6e819b6e0d62f79f64ec83be99f5763'
    if escolhidos != {'deepseek-r1:latest'} or disponiveis.get('deepseek-r1:latest') != esperado:
        raise ValueError('O juiz mudou desde o experimento anterior. Registrar outro protocolo antes de continuar.')
    return {nome: disponiveis[nome] for nome in sorted(escolhidos)}


def acrescentar(arquivo, valor):
    """Acrescenta um registro sem substituir arquivos abertos pelo OneDrive."""
    with arquivo.open('a', encoding='utf-8', newline='\n') as destino:
        destino.write(json.dumps(valor, ensure_ascii=False, allow_nan=False) + '\n')
        destino.flush()
        os.fsync(destino.fileno())


def medir_registrando(metrica, evidencia):
    """Registra a métrica no DeepEval; nota baixa é resultado, não erro técnico."""
    from deepeval import assert_test
    try:
        assert_test(evidencia, [metrica], run_async=False)
    except AssertionError:
        # O assert_test reprova notas abaixo do corte. Preservamos a nota e
        # deixamos o pytest reprovar o caso depois de avaliar as três métricas.
        if metrica.score is None or getattr(metrica, 'error', None):
            raise


class Rodada:
    def __init__(self, versao, retomar=False):
        self.origem, self.captura, self.golden = carregar(versao)
        self.meta = assinatura(versao, self.origem)
        self.pasta = RAIZ / 'resultados/frente_b'
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.log = self.pasta / f'{TIPO}_{versao}.jsonl'
        self.saida = self.pasta / f'{TIPO}_{versao}.json'
        self.notas = {}
        for referencia in self.pasta.glob('*.json'):
            outra = ler(referencia).get('metadata', {})
            if outra.get('protocolo') == 'qwen_capturado_v1':
                for campo in ('juizes', 'digests_juizes', 'temperatura_juiz', 'opcoes_juiz', 'thresholds', 'bibliotecas', 'codigo_sha256'):
                    if outra[campo] != self.meta[campo]:
                        raise ValueError(f'O protocolo mudou em {campo}; não misturar rodadas.')
        if self.saida.exists():
            raise ValueError(f'Rodada já encerrada: {self.saida}. Preserve o resultado.')
        if self.log.exists():
            if not retomar:
                raise ValueError('Já existe uma rodada parcial. Use --retomar.')
            linhas = [json.loads(l) for l in self.log.read_text(encoding='utf-8').splitlines()]
            if not linhas or linhas[0] != {'metadata': self.meta}:
                raise ValueError('Captura, código, juiz ou bibliotecas mudaram; retomada recusada.')
            permitidos = {(c['id'], nome) for c in self.golden for nome in NOMES}
            for nota in linhas[1:]:
                chave = (nota['caso_id'], nota['metrica'])
                if chave not in permitidos or chave in self.notas:
                    raise ValueError('Log com resultado duplicado ou desconhecido.')
                self.notas[chave] = nota
        else:
            # Criação exclusiva evita duas execuções iniciadas no mesmo arquivo.
            with self.log.open('x', encoding='utf-8') as destino:
                destino.write(json.dumps({'metadata': self.meta}, ensure_ascii=False) + '\n')

    def avaliar(self, indice):
        from src.deepeval.casos import montar_casos
        from src.deepeval.juiz import obter_metricas_base
        caso, registro = self.golden[indice], self.captura['resultados'][indice]
        contexto = contextos(registro)
        ultima, conversa = montar_casos(registro['turnos'], registro['respostas'], caso['expected_output'], contexto)
        for nome, metrica, evidencia in zip(NOMES, obter_metricas_base(), (ultima, ultima, conversa), strict=True):
            chave = (caso['id'], nome)
            if chave in self.notas:
                print(f'{caso["id"]}: {nome} já registrado; preservado.', flush=True)
                continue
            nota = {'caso_id': caso['id'], 'session_id': registro['session_id'], 'metrica': nome,
                    'threshold': metrica.threshold, 'score': None, 'passou': None,
                    'input_avaliado': evidencia.input, 'resposta_avaliada': evidencia.actual_output,
                    'retrieval_context': contexto}
            if nome == 'Faithfulness' and not contexto:
                nota.update(status='nao_avaliavel', razao='Nenhum contexto RAG observado nesta sessão; não é zero nem aprovação. Revisar se houve recusa legítima, ausência de tool call ou falta de telemetria.')
            else:
                print(f'{caso["id"]}/{len(self.golden)}: executando {nome}...', flush=True)
                try:
                    medir_registrando(metrica, evidencia)
                    if metrica.score is None or not math.isfinite(metrica.score):
                        raise ValueError('Juiz não produziu uma nota finita.')
                    nota.update(status='avaliado', score=metrica.score,
                                passou=bool(metrica.is_successful()), razao=metrica.reason)
                    for campo in ('statements', 'claims', 'verdicts'):
                        valores = getattr(metrica, campo, None)
                        if valores is not None:
                            nota[campo] = [v.model_dump() if hasattr(v, 'model_dump') else v for v in valores]
                except Exception as erro:
                    nota.update(status='erro', erro=f'{type(erro).__name__}: {erro}')
                nota['repeticoes_transporte'] = getattr(metrica.model, 'transport_retries', 0)
            # Falha ao gravar interrompe a rodada. Não repete chamadas para melhorar notas.
            acrescentar(self.log, nota)
            self.notas[chave] = nota
        return [self.notas[(caso['id'], n)] for n in NOMES]

    def encerrar(self):
        completo = len(self.notas) == len(self.golden) * 3
        if not completo:
            print(f'Rodada parcial: {len(self.notas)}/{len(self.golden) * 3} registros. Retome com MASP_QWEN_RETOMAR=1.')
            return
        resumo = {}
        for nome in NOMES:
            notas = [n for n in self.notas.values() if n['metrica'] == nome]
            validas = [n for n in notas if n['status'] == 'avaliado']
            resumo[nome] = {'avaliados': len(validas), 'aprovados': sum(n['passou'] for n in validas),
                            'erros': sum(n['status'] == 'erro' for n in notas),
                            'nao_avaliaveis': sum(n['status'] == 'nao_avaliavel' for n in notas),
                            'media': sum(n['score'] for n in validas) / len(validas) if validas else None}
        dados = {'metadata': {**self.meta, 'status': 'finalizado_com_erros' if any(n['status'] == 'erro' for n in self.notas.values()) else 'finalizado', 'harness': self.captura['metadata'],
                             'limites': ['Faithfulness sem RAG registrado fica não avaliável.',
                                        'Sem contexto real, G-Eval também tem suporte factual limitado.',
                                        'AR/F avaliam a última resposta; G-Eval considera a conversa.',
                                        'Notas não comprovam uso autônomo da ferramenta nem aprovação integral do golden.',
                                        'DeepEval agrega por caso; AgentCore pode produzir mais de uma nota por sessão.']},
                 'resumo': resumo, 'log_sha256': sha(self.log), 'resultados': list(self.notas.values())}
        with self.saida.open('x', encoding='utf-8') as destino:
            json.dump(dados, destino, ensure_ascii=False, indent=2, allow_nan=False)
        print(f'Resultado salvo: {self.saida}', flush=True)

