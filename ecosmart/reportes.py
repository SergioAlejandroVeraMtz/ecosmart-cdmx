"""Construcción y exportación de reportes: JSON, texto, máscara y superposiciones."""

from datetime import datetime

import cv2
import numpy as np

from . import config as cfg
from .io_seguro import a_tipos_json, escribir_json_atomico

AVISO = (
    "Resultados orientativos. La cobertura verde se mide sobre la imagen y no "
    "equivale a superficie real del terreno. El índice de aire es una estimación "
    "visual sin calibrar y no sustituye a la red SIMAT."
)


def datos_para_progreso(veg, air=None):
    """Resumen escalar que se guarda en el progreso del usuario."""
    datos = veg.a_diccionario()
    if air is not None:
        datos["categoria_aire"] = air.categoria
    return datos


def construir_reporte(usuario, veg, air=None):
    """Reporte completo en tipos nativos, listo para escribir como JSON."""
    return a_tipos_json({
        "version_esquema": cfg.VERSION_ESQUEMA,
        "usuario": usuario,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "vegetacion": veg.a_diccionario(),
        "aire": air.a_diccionario() if air is not None else None,
        "aviso": AVISO,
    })


def resumen_texto(reporte):
    """Texto corto para consola o para mostrar en la interfaz."""
    v = reporte["vegetacion"]
    lineas = [
        f"Usuario: {reporte['usuario']}",
        f"Cobertura verde: {v['porcentaje_cobertura']:.2f} % ({v['pixeles_verdes']} de {v['pixeles_totales']} píxeles)",
        f"Áreas verdes separadas: {v['numero_areas']}",
        f"Área promedio: {v['tamano_promedio_area']} px | Área máxima: {v['tamano_maximo_area']} px",
        f"Saturación media (vigor): {v['saturacion_media']:.3f}",
        f"Distribución espacial: {v['coeficiente_distribucion']:.3f}",
        f"Evaluación de cobertura: {v['evaluacion']}",
    ]
    if reporte.get("aire"):
        a = reporte["aire"]
        lineas.append(f"Índice orientativo de aire: {a['indice_orientativo']} ({a['categoria']}), {a['confianza']}")
    lineas.append("Recomendaciones:")
    lineas.extend(f"  - {texto}" for texto in v["recomendaciones"])
    lineas.append(reporte["aviso"])
    return "\n".join(lineas)


def guardar_reporte(reporte, ruta):
    return escribir_json_atomico(reporte, ruta)


def guardar_mascara(mascara, ruta):
    """Guarda la máscara binaria como PNG."""
    if not cv2.imwrite(str(ruta), mascara):
        raise OSError(f"No se pudo escribir la máscara en {ruta}")
    return ruta


def superponer(imagen_bgr, mascara, color=(0, 255, 0), alpha=0.45):
    """Pinta de `color` los píxeles de vegetación sobre la imagen original."""
    capa = imagen_bgr.copy()
    capa[mascara > 0] = color
    return cv2.addWeighted(capa, alpha, imagen_bgr, 1.0 - alpha, 0.0)


def convertir_para_mostrar(imagen_bgr):
    """BGR a RGB, el orden que esperan Tk y Pillow."""
    if imagen_bgr.ndim == 2:
        return cv2.cvtColor(imagen_bgr, cv2.COLOR_GRAY2RGB)
    return cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2RGB)


def mascara_a_imagen(mascara):
    """Convierte una máscara de una banda en una imagen BGR en blanco y negro."""
    return cv2.cvtColor(np.asarray(mascara, dtype=np.uint8), cv2.COLOR_GRAY2BGR)
