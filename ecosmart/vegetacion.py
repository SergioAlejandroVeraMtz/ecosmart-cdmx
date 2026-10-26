"""Análisis de áreas verdes: segmentación por color y métricas de la máscara.

Flujo general de analizar():
1. Validar la imagen de entrada.
2. Corregir iluminación con una curva gamma (aclara sombras).
3. Segmentar píxeles verdes en HSV con varios rangos y limpiarlos con morfología.
4. Calcular cobertura, componentes conectados, distribución espacial y vigor.
5. Evaluar la cobertura con los umbrales de config.UMBRAL_*.

Limitaciones que conviene declarar en cualquier reporte:
- La cobertura se mide sobre la imagen, no sobre superficie real del terreno.
- La "salud" es la saturación media del verde (un proxy). NO es NDVI, que
  requiere una banda infrarroja que una foto de celular no tiene.
"""

from dataclasses import dataclass, field

import cv2
import numpy as np

from . import config as cfg
from .imagenes import validar_imagen_bgr


@dataclass
class ResultadoVegetacion:
    """Métricas del análisis de áreas verdes de una imagen."""

    porcentaje_cobertura: float
    pixeles_verdes: int
    pixeles_totales: int
    numero_areas: int
    tamano_promedio_area: float
    tamano_maximo_area: int
    saturacion_media: float
    diversidad_tonal: float
    indice_verdor_exg: float
    cuadrantes: list
    coeficiente_distribucion: float
    evaluacion: str
    recomendaciones: tuple
    mascara: np.ndarray = field(repr=False, compare=False)

    def a_diccionario(self):
        """Métricas como tipos nativos, sin la máscara (que no se serializa a JSON)."""
        return {
            "porcentaje_cobertura": round(float(self.porcentaje_cobertura), 2),
            "pixeles_verdes": int(self.pixeles_verdes),
            "pixeles_totales": int(self.pixeles_totales),
            "numero_areas": int(self.numero_areas),
            "tamano_promedio_area": round(float(self.tamano_promedio_area), 1),
            "tamano_maximo_area": int(self.tamano_maximo_area),
            "saturacion_media": round(float(self.saturacion_media), 3),
            "diversidad_tonal": round(float(self.diversidad_tonal), 3),
            "indice_verdor_exg": round(float(self.indice_verdor_exg), 3),
            "cuadrantes": [round(float(c), 2) for c in self.cuadrantes],
            "coeficiente_distribucion": round(float(self.coeficiente_distribucion), 3),
            "evaluacion": self.evaluacion,
            "recomendaciones": list(self.recomendaciones),
        }


def corregir_iluminacion(imagen, gamma=None):
    """Aplica una curva gamma por tabla de búsqueda (LUT).

    La fórmula es salida = (entrada/255)^(1/gamma) * 255. Con gamma > 1 la
    imagen se aclara; con gamma < 1 se oscurece.
    """
    gamma = cfg.GAMMA_ILUMINACION if gamma is None else gamma
    if gamma <= 0:
        raise ValueError("El valor de gamma debe ser positivo")
    valores = np.arange(256, dtype=np.float64) / 255.0
    tabla = np.clip(np.power(valores, 1.0 / gamma) * 255.0, 0, 255).astype(np.uint8)
    return cv2.LUT(imagen, tabla)


def _kernel():
    """Kernel cuadrado impar, según config.TAMANO_KERNEL."""
    lado = int(cfg.TAMANO_KERNEL)
    if lado % 2 == 0:
        lado += 1
    return np.ones((lado, lado), np.uint8)


def segmentar_vegetacion(imagen_bgr, rangos=None):
    """Devuelve una máscara binaria (0 o 255) con los píxeles de vegetación."""
    rangos = cfg.RANGOS_VERDE_HSV if rangos is None else rangos
    hsv = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2HSV)
    mascara = np.zeros(hsv.shape[:2], np.uint8)
    for bajo, alto in rangos:
        mascara |= cv2.inRange(hsv, np.array(bajo, np.uint8), np.array(alto, np.uint8))

    # Apertura elimina ruido aislado; cierre rellena huecos dentro de las copas.
    kernel = _kernel()
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, kernel)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel)
    return mascara


def tamanos_de_areas(mascara):
    """Tamaño en píxeles de cada área verde conectada (8 vecinos)."""
    _, etiquetas = cv2.connectedComponents(mascara, connectivity=8)
    tamanos = np.bincount(etiquetas.ravel())[1:]  # la etiqueta 0 es el fondo
    return tamanos[tamanos > 0]


def proporciones_por_cuadrante(mascara, filas=2, columnas=2):
    """Porcentaje de vegetación en cada celda de una cuadrícula.

    El orden es de izquierda a derecha y de arriba hacia abajo.
    """
    alto, ancho = mascara.shape
    proporciones = []
    for i in range(filas):
        for j in range(columnas):
            celda = mascara[i * alto // filas:(i + 1) * alto // filas,
                            j * ancho // columnas:(j + 1) * ancho // columnas]
            total = max(celda.size, 1)
            proporciones.append(100.0 * np.count_nonzero(celda) / total)
    return proporciones


def coeficiente_distribucion(proporciones):
    """Puntaje 0..1 de qué tan repartida está la vegetación (1 = uniforme).

    Se calcula como 1 / (1 + coeficiente de variación). Si no hay vegetación,
    devuelve 0: no tiene sentido decir que "nada" está bien distribuido.
    """
    valores = np.asarray(proporciones, dtype=np.float64) / 100.0
    media = valores.mean()
    if media <= 0:
        return 0.0
    coef_variacion = valores.std() / media
    return float(1.0 / (1.0 + coef_variacion))


def indice_exg_medio(imagen_bgr, mascara):
    """Índice de verdor Excess Green (2g - r - b) promediado sobre la máscara.

    Usa coordenadas cromáticas, así que es menos sensible al brillo que el RGB.
    Va de -1 a 2; valores mayores a 0 indican dominancia del verde.
    """
    pixeles = imagen_bgr[mascara > 0].astype(np.float64)
    if pixeles.size == 0:
        return 0.0
    b, g, r = pixeles[:, 0], pixeles[:, 1], pixeles[:, 2]
    total = r + g + b + 1e-6
    exg = 2.0 * (g / total) - (r / total) - (b / total)
    return float(exg.mean())


def evaluar(cobertura, saturacion, distribucion):
    """Clasifica la imagen según los umbrales de config.UMBRAL_*."""
    niveles = (
        ("EXCELENTE", cfg.UMBRAL_EXCELENTE),
        ("BUENA", cfg.UMBRAL_BUENA),
        ("REGULAR", cfg.UMBRAL_REGULAR),
    )
    for nombre, umbral in niveles:
        if (cobertura >= umbral["cobertura"]
                and saturacion >= umbral["saturacion"]
                and distribucion >= umbral["distribucion"]):
            return nombre
    return "INSUFICIENTE"


def analizar(imagen):
    """Análisis completo de áreas verdes de una imagen BGR.

    Lanza ValueError si la imagen no es válida. No devuelve diccionarios de
    error: quien llama decide cómo mostrar el problema.
    """
    validar_imagen_bgr(imagen)
    procesada = corregir_iluminacion(imagen)
    mascara = segmentar_vegetacion(procesada)

    total = int(mascara.size)
    verdes = int(np.count_nonzero(mascara))
    cobertura = 100.0 * verdes / total

    areas = tamanos_de_areas(mascara)
    proporciones = proporciones_por_cuadrante(mascara)
    distribucion = coeficiente_distribucion(proporciones)

    if verdes > 0:
        hsv = cv2.cvtColor(procesada, cv2.COLOR_BGR2HSV)
        tono = hsv[:, :, 0][mascara > 0].astype(np.float64)
        saturacion_pixeles = hsv[:, :, 1][mascara > 0].astype(np.float64)
        saturacion = float(saturacion_pixeles.mean()) / 255.0
        diversidad = float(tono.std()) / 180.0
        exg = indice_exg_medio(procesada, mascara)
    else:
        saturacion = diversidad = exg = 0.0

    evaluacion = evaluar(cobertura, saturacion, distribucion)
    return ResultadoVegetacion(
        porcentaje_cobertura=cobertura,
        pixeles_verdes=verdes,
        pixeles_totales=total,
        numero_areas=int(areas.size),
        tamano_promedio_area=float(areas.mean()) if areas.size else 0.0,
        tamano_maximo_area=int(areas.max()) if areas.size else 0,
        saturacion_media=saturacion,
        diversidad_tonal=diversidad,
        indice_verdor_exg=exg,
        cuadrantes=proporciones,
        coeficiente_distribucion=distribucion,
        evaluacion=evaluacion,
        recomendaciones=cfg.RECOMENDACIONES_VEGETACION[evaluacion],
        mascara=mascara,
    )
