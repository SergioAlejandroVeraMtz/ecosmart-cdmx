"""Gráficas del análisis. Usa matplotlib.figure.Figure sin pyplot, así se pueden
incrustar en Tkinter y también guardar como PNG desde la línea de comandos."""

import cv2
import numpy as np
from matplotlib.figure import Figure

from . import reportes

NOMBRES_CUADRANTES = ("Sup. izq.", "Sup. der.", "Inf. izq.", "Inf. der.")


def figura_resumen(imagen_bgr, veg):
    """Tres paneles: imagen original, máscara de vegetación y cobertura por cuadrante."""
    figura = Figure(figsize=(10, 3.6), dpi=100)

    eje_imagen = figura.add_subplot(1, 3, 1)
    eje_imagen.imshow(reportes.convertir_para_mostrar(imagen_bgr))
    eje_imagen.set_title("Imagen original")
    eje_imagen.axis("off")

    eje_mascara = figura.add_subplot(1, 3, 2)
    eje_mascara.imshow(veg.mascara, cmap="Greens", vmin=0, vmax=255)
    eje_mascara.set_title(f"Vegetación: {veg.porcentaje_cobertura:.1f} %")
    eje_mascara.axis("off")

    eje_cuadrantes = figura.add_subplot(1, 3, 3)
    barras = eje_cuadrantes.bar(NOMBRES_CUADRANTES, veg.cuadrantes, color="#2e7d32")
    eje_cuadrantes.set_ylim(0, 100)
    eje_cuadrantes.set_ylabel("% de verde")
    eje_cuadrantes.set_title("Distribución por cuadrante")
    eje_cuadrantes.bar_label(barras, fmt="%.1f", fontsize=8)

    figura.tight_layout()
    return figura


def figura_tonos(imagen_bgr, veg):
    """Histograma de tonos (H) y de saturación (S) solo de los píxeles verdes."""
    figura = Figure(figsize=(9, 3.2), dpi=100)
    hsv = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2HSV)
    mascara = veg.mascara > 0

    eje_tono = figura.add_subplot(1, 2, 1)
    if mascara.any():
        eje_tono.hist(hsv[:, :, 0][mascara], bins=36, range=(0, 180), color="#43a047")
    eje_tono.set_title("Tonos de verde (matiz H)")
    eje_tono.set_xlabel("H (0-179)")
    eje_tono.set_ylabel("píxeles")

    eje_sat = figura.add_subplot(1, 2, 2)
    if mascara.any():
        eje_sat.hist(hsv[:, :, 1][mascara], bins=32, range=(0, 255), color="#7cb342")
    eje_sat.set_title("Saturación (proxy de vigor)")
    eje_sat.set_xlabel("S (0-255)")

    figura.tight_layout()
    return figura


def figura_superposicion(imagen_bgr, veg):
    """La imagen con la vegetación resaltada en verde."""
    figura = Figure(figsize=(6, 4.5), dpi=100)
    eje = figura.add_subplot(1, 1, 1)
    superpuesta = reportes.superponer(imagen_bgr, veg.mascara)
    eje.imshow(reportes.convertir_para_mostrar(superpuesta))
    eje.set_title(f"Cobertura verde: {veg.porcentaje_cobertura:.1f} %")
    eje.axis("off")
    figura.tight_layout()
    return figura


def guardar_figura(figura, ruta):
    """Guarda una figura como PNG."""
    figura.savefig(str(ruta), dpi=120, bbox_inches="tight")
    return ruta


def promedio_tono(imagen_bgr, mascara):
    """Matiz medio de los píxeles verdes (0-179), o None si no hay vegetación."""
    hsv = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2HSV)
    seleccion = hsv[:, :, 0][mascara > 0]
    return float(np.mean(seleccion)) if seleccion.size else None
