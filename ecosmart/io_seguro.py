"""Entrada/salida segura: conversión a JSON y escritura atómica.

Dos problemas de la versión anterior se resuelven aquí:
- json.dump fallaba a mitad de escritura al encontrar un arreglo de NumPy y
  dejaba un archivo truncado. Ahora los arreglos se descartan antes de escribir.
- Si la escritura fallaba, el archivo anterior ya estaba destruido. Ahora se
  escribe a un temporal y solo después se reemplaza el archivo original.
"""

import json
import math
import os
import tempfile
from pathlib import Path

import numpy as np


def a_tipos_json(objeto):
    """Devuelve una copia del objeto con tipos nativos de Python.

    - Los diccionarios pierden las claves cuyo valor es un arreglo de NumPy.
    - Los escalares de NumPy se convierten a int/float nativos.
    - Los valores no finitos (nan, inf) se convierten a None.
    """
    if isinstance(objeto, dict):
        return {
            str(clave): a_tipos_json(valor)
            for clave, valor in objeto.items()
            if not isinstance(valor, np.ndarray)
        }
    if isinstance(objeto, (list, tuple)):
        return [a_tipos_json(v) for v in objeto if not isinstance(v, np.ndarray)]
    if isinstance(objeto, np.generic):
        objeto = objeto.item()
    if isinstance(objeto, float) and not math.isfinite(objeto):
        return None
    if isinstance(objeto, Path):
        return str(objeto)
    return objeto


def escribir_json_atomico(datos, ruta):
    """Escribe `datos` como JSON en `ruta` sin dejar archivos a medias.

    El contenido se escribe primero en un archivo temporal de la misma carpeta
    y después se reemplaza el destino con os.replace, que es atómico en el
    mismo sistema de archivos. Si algo falla, el destino original no cambia.
    """
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(a_tipos_json(datos), indent=2, ensure_ascii=False, allow_nan=False)

    descriptor, temporal = tempfile.mkstemp(dir=ruta.parent, prefix=ruta.name + ".", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
            archivo.write(texto)
            archivo.flush()
            os.fsync(archivo.fileno())
        os.replace(temporal, ruta)
    except BaseException:
        if os.path.exists(temporal):
            os.remove(temporal)
        raise
    return ruta
