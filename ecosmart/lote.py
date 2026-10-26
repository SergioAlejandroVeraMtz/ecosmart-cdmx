"""Análisis por lote de una carpeta de imágenes, con exportación a CSV.

Una imagen con error no detiene el lote: se registra en `errores` y el
proceso continúa con las demás.
"""

import csv
from pathlib import Path

from . import aire, imagenes, vegetacion

EXTENSIONES = imagenes.EXTENSIONES_IMAGEN

CAMPOS_CSV = (
    "archivo",
    "cobertura_pct",
    "areas",
    "area_promedio_px",
    "saturacion_media",
    "distribucion",
    "evaluacion",
    "indice_aire",
    "categoria_aire",
)


def listar_imagenes(carpeta):
    """Archivos de imagen de la carpeta (sin subcarpetas), ordenados por nombre."""
    carpeta = Path(carpeta)
    if not carpeta.is_dir():
        raise NotADirectoryError(f"No es una carpeta: {carpeta}")
    return sorted(p for p in carpeta.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONES)


def fila_para(ruta, mes=None):
    """Analiza una imagen y devuelve una fila lista para el CSV."""
    imagen = imagenes.redimensionar_maximo(imagenes.cargar_imagen(ruta))
    veg = vegetacion.analizar(imagen)
    air = aire.estimar(imagen, mes=mes)
    return {
        "archivo": Path(ruta).name,
        "cobertura_pct": round(veg.porcentaje_cobertura, 2),
        "areas": veg.numero_areas,
        "area_promedio_px": round(veg.tamano_promedio_area, 1),
        "saturacion_media": round(veg.saturacion_media, 3),
        "distribucion": round(veg.coeficiente_distribucion, 3),
        "evaluacion": veg.evaluacion,
        "indice_aire": air.indice,
        "categoria_aire": air.categoria,
    }


def escribir_csv(filas, ruta):
    """Escribe las filas en CSV con separador de coma y codificación UTF-8 con BOM (Excel)."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=CAMPOS_CSV)
        escritor.writeheader()
        escritor.writerows(filas)
    return ruta


def analizar_carpeta(carpeta, ruta_csv, mes=None):
    """Procesa todas las imágenes de `carpeta` y guarda un CSV con los resultados.

    Devuelve un diccionario con las filas procesadas, los errores por archivo
    y la ruta del CSV.
    """
    filas, errores = [], []
    for ruta in listar_imagenes(carpeta):
        try:
            filas.append(fila_para(ruta, mes=mes))
        except (ValueError, OSError) as exc:
            errores.append({"archivo": ruta.name, "motivo": str(exc)})
    escribir_csv(filas, ruta_csv)
    return {"procesadas": len(filas), "errores": errores, "filas": filas, "csv": Path(ruta_csv)}


def promedio_cobertura(filas):
    """Cobertura media de un conjunto de filas (0 si no hay filas)."""
    if not filas:
        return 0.0
    return round(sum(f["cobertura_pct"] for f in filas) / len(filas), 2)
