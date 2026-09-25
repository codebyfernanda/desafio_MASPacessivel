# Estudo: nomes claros, responsabilidades explícitas e comentários sobre decisões.
# O formato legado é adaptado na fronteira de entrada. O arquivo golden
# permanece intacto e seu esperado nunca é enviado ao agente como instrução.

import re

def separar_turnos(entrada):
    """Converte o formato legado T1/T2 em mensagens reais, sem mudar o dataset."""
    if not isinstance(entrada, str) or not entrada.strip():
        raise ValueError("O input deve ser um texto não vazio.")
    turnos = re.split(r"\s*/\s*T\d+:\s*", entrada.strip())
    turnos[0] = re.sub(r"^T\d+:\s*", "", turnos[0])
    mensagens = []
    for turno in turnos:
        texto = turno.strip()
        if texto.startswith('"') and texto.endswith('"'):
            texto = texto[1:-1]
        mensagens.append(re.sub(r'\\+"', '"', texto))
    return mensagens

