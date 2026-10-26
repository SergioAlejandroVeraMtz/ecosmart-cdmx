"""Índice visual orientativo de calidad del aire.

IMPORTANTE: esto NO es una medición. Una foto de celular no permite medir
partículas ni ozono. El valor se estima a partir de nitidez, contraste, bordes
y saturación, que se degradan con la bruma. Los pesos y escalas son supuestos
simples sin calibrar con datos reales. Para un dato oficial, usar la red SIMAT
de la Ciudad de México.

Las categorías siguen las bandas del IMECA (0-50 buena, 51-100 regular,
101-150 mala, 151-200 muy mala). La cifra se limita a 200.
"""

from dataclasses import dataclass
from datetime import datetime

import cv2

from . import config as cfg
from .imagenes import validar_imagen_bgr

BANDAS = (
    (50.0, "Buena"),
    (100.0, "Regular"),
    (150.0, "Mala"),
    (200.0, "Muy mala"),
)

RECOMENDACIONES_AIRE = {
    "Buena": (
        "Condiciones favorables para actividades al aire libre.",
    ),
    "Regular": (
        "Las personas sensibles deben limitar el esfuerzo físico prolongado al aire libre.",
    ),
    "Mala": (
        "Reducir la actividad física intensa al aire libre.",
        "Usar cubrebocas de alta filtración si es necesario salir.",
    ),
    "Muy mala": (
        "Evitar actividades al aire libre.",
        "Mantener las ventanas cerradas y usar purificador si está disponible.",
        "Consultar a un médico ante síntomas respiratorios.",
    ),
}

CONFIANZA_BAJA = "baja: estimación visual sin calibrar"


@dataclass(frozen=True)
class ResultadoAire:
    """Estimación visual del aire. Ver la advertencia del módulo."""

    indice: float
    categoria: str
    ajuste_temporada: float
    caracteristicas: dict
    recomendaciones: tuple
    confianza: str = CONFIANZA_BAJA

    def a_diccionario(self):
        return {
            "indice_orientativo": round(float(self.indice), 1),
            "categoria": self.categoria,
            "ajuste_temporada": float(self.ajuste_temporada),
            "caracteristicas": {k: round(float(v), 4) for k, v in self.caracteristicas.items()},
            "recomendaciones": list(self.recomendaciones),
            "confianza": self.confianza,
        }


def caracteristicas(imagen):
    """Mide nitidez, contraste, densidad de bordes y saturación de la imagen."""
    validar_imagen_bgr(imagen)
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(imagen, cv2.COLOR_BGR2HSV)
    bordes = cv2.Canny(gris, 100, 200)
    return {
        "nitidez": float(cv2.Laplacian(gris, cv2.CV_64F).var()),
        "contraste": float(gris.std()),
        "densidad_bordes": float((bordes > 0).mean()),
        "saturacion": float(hsv[:, :, 1].mean()) / 255.0,
    }


def puntaje_limpieza(c):
    """Combina las características en un valor 0..1 (1 = aire aparentemente limpio)."""
    nitidez = min(c["nitidez"] / cfg.ESCALA_NITIDEZ, 1.0)
    contraste = min(c["contraste"] / cfg.ESCALA_CONTRASTE, 1.0)
    bordes = min(c["densidad_bordes"] / cfg.ESCALA_BORDES, 1.0)
    saturacion = min(c["saturacion"] / cfg.ESCALA_SATURACION, 1.0)
    return 0.35 * nitidez + 0.25 * contraste + 0.20 * bordes + 0.20 * saturacion


def categoria_para(indice):
    """Nombre de la banda IMECA que corresponde al índice."""
    for limite, nombre in BANDAS:
        if indice <= limite:
            return nombre
    return BANDAS[-1][1]


def factor_temporada(mes):
    """Multiplicador por temporada seca (supuesto simple, ver config)."""
    return cfg.AJUSTE_TEMPORADA_SECA if mes in cfg.MESES_TEMPORADA_SECA else 1.0


def estimar(imagen, mes=None):
    """Estimación orientativa del índice de aire para una imagen BGR.

    `mes` (1-12) controla el ajuste de temporada. Si es None se usa el mes actual.
    """
    c = caracteristicas(imagen)
    base = 200.0 * (1.0 - puntaje_limpieza(c))
    if mes is None:
        mes = datetime.now().month
    factor = factor_temporada(mes)
    indice = min(round(base * factor, 1), 200.0)
    categoria = categoria_para(indice)
    return ResultadoAire(
        indice=indice,
        categoria=categoria,
        ajuste_temporada=factor,
        caracteristicas=c,
        recomendaciones=RECOMENDACIONES_AIRE[categoria],
    )
