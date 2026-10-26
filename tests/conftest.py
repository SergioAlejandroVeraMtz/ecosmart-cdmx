import sys
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


@pytest.fixture
def verde_claro():
    imagen = np.zeros((600, 400, 3), np.uint8)
    imagen[:] = (60, 180, 60)  # BGR
    return imagen


@pytest.fixture
def cielo():
    imagen = np.zeros((600, 400, 3), np.uint8)
    imagen[:] = (235, 206, 135)  # BGR, azul claro
    return imagen


@pytest.fixture(autouse=True)
def restaurar_config():
    """Cada prueba empieza con los parámetros originales de config.py."""
    from ecosmart import config as cfg

    originales = {k: getattr(cfg, k) for k in dir(cfg) if k.isupper()}
    yield
    for clave, valor in originales.items():
        setattr(cfg, clave, valor)
