"""Carga de parámetros personalizados desde un archivo JSON, con validación.

Ejemplo de archivo (ecosmart.json):
    {"GAMMA_ILUMINACION": 1.4, "AJUSTE_TEMPORADA_SECA": 1.2}

Solo se aceptan claves conocidas y valores dentro de un rango razonable. Así un
error de tecleo falla al cargar y no produce resultados silenciosamente incorrectos.
"""

import json
from pathlib import Path

from . import config as cfg

# Parámetro -> (mínimo, máximo, tipo nativo esperado)
CAMPOS = {
    "GAMMA_ILUMINACION": (0.1, 5.0, float),
    "TAMANO_KERNEL": (1, 31, int),
    "AJUSTE_TEMPORADA_SECA": (1.0, 2.0, float),
    "PUNTOS_POR_NIVEL": (1, 10000, int),
    "BONO_MAXIMO_COBERTURA": (0.0, 2.0, float),
    "ESCALA_NITIDEZ": (1.0, 100000.0, float),
    "ESCALA_CONTRASTE": (1.0, 255.0, float),
    "ESCALA_BORDES": (0.001, 1.0, float),
    "ESCALA_SATURACION": (0.01, 1.0, float),
}


def validar(datos):
    """Revisa un diccionario de parámetros y devuelve una copia limpia."""
    if not isinstance(datos, dict):
        raise ValueError("La configuración debe ser un objeto JSON")
    limpio = {}
    for clave, valor in datos.items():
        if clave not in CAMPOS:
            raise ValueError(f"Parámetro desconocido: {clave}. Válidos: {', '.join(sorted(CAMPOS))}")
        minimo, maximo, tipo = CAMPOS[clave]
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise ValueError(f"{clave} debe ser numérico")
        if not minimo <= valor <= maximo:
            raise ValueError(f"{clave}={valor} está fuera del rango [{minimo}, {maximo}]")
        limpio[clave] = tipo(valor)
    return limpio


def cargar(ruta):
    """Lee y valida el archivo. Si no existe, devuelve un diccionario vacío."""
    ruta = Path(ruta)
    if not ruta.exists():
        return {}
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido en {ruta.name}: {exc}") from exc
    return validar(datos)


def aplicar(parametros):
    """Sobrescribe los parámetros en el módulo config. Devuelve los aplicados."""
    for clave, valor in parametros.items():
        setattr(cfg, clave, valor)
    return dict(parametros)
