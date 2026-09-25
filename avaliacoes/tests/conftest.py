"""Evita reutilizar temporários criados por outra conta do Windows."""
from pathlib import Path
import tempfile
import uuid


def pytest_configure(config):
    if config.option.basetemp is None:
        # --basetemp é limpo pelo pytest. Escolhemos um caminho novo e exclusivo,
        # diretamente abaixo do TEMP, sem apontar para dados ou resultados.
        raiz = Path(tempfile.gettempdir()).resolve()
        temporario = raiz / ('masp-pytest-' + uuid.uuid4().hex)
        if temporario.parent != raiz or temporario.exists():
            raise RuntimeError('Não foi possível escolher um temporário exclusivo.')
        config.option.basetemp = str(temporario)
