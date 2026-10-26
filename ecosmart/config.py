"""Parámetros del proyecto EcoSmart.

Todos los umbrales, rangos y constantes del análisis viven aquí para que sean
fáciles de revisar, de ajustar (ver configuracion.py) y de citar en el reporte.
Las funciones leen estos valores en tiempo de ejecución, no al importar el
módulo, así que un cambio con configuracion.aplicar() surte efecto de inmediato.
"""

from pathlib import Path

__all__ = [
    "VERSION_ESQUEMA", "NOMBRE_APP", "USUARIO_POR_DEFECTO", "DIRECTORIO_DATOS",
    "NOMBRE_ARCHIVO_PROGRESO", "RANGOS_VERDE_HSV", "GAMMA_ILUMINACION",
    "TAMANO_KERNEL", "UMBRAL_EXCELENTE", "UMBRAL_BUENA", "UMBRAL_REGULAR",
    "RECOMENDACIONES_VEGETACION", "ESCALA_NITIDEZ", "ESCALA_CONTRASTE",
    "ESCALA_BORDES", "ESCALA_SATURACION", "AJUSTE_TEMPORADA_SECA",
    "MESES_TEMPORADA_SECA", "PUNTOS_BASE_POR_ODS", "BONO_MAXIMO_COBERTURA",
    "PUNTOS_POR_NIVEL", "MEDALLAS", "NOMBRES_ODS",
]

VERSION_ESQUEMA = 2
NOMBRE_APP = "EcoSmart CDMX"
USUARIO_POR_DEFECTO = "usuario_local"

# Carpeta donde se guarda el progreso del usuario (fuera del directorio de trabajo).
DIRECTORIO_DATOS = Path.home() / ".ecosmart"
NOMBRE_ARCHIVO_PROGRESO = "progreso_ods.json"

# ---------------------------------------------------------------------------
# Segmentación de vegetación (espacio HSV de OpenCV: H 0-179, S y V 0-255)
# ---------------------------------------------------------------------------
RANGOS_VERDE_HSV = (
    ((35, 40, 40), (85, 255, 255)),   # verde típico: hojas y pasto
    ((25, 40, 40), (35, 255, 255)),   # verde-amarillo: vegetación clara o seca
    ((85, 40, 40), (95, 255, 255)),   # verde-azulado: algunas especies
)

# Gamma > 1 aclara sombras. Con 0.8 (versión anterior) los verdes oscuros
# caían bajo el umbral V >= 40 y desaparecían de la máscara.
GAMMA_ILUMINACION = 1.25

# Lado del kernel morfológico en píxeles (debe ser impar; si no, se suma 1).
TAMANO_KERNEL = 5

# ---------------------------------------------------------------------------
# Evaluación de cobertura verde (porcentaje de la imagen cubierto por vegetación)
# ---------------------------------------------------------------------------
UMBRAL_EXCELENTE = {"cobertura": 30.0, "saturacion": 0.70, "distribucion": 0.60}
UMBRAL_BUENA = {"cobertura": 20.0, "saturacion": 0.50, "distribucion": 0.40}
UMBRAL_REGULAR = {"cobertura": 10.0, "saturacion": 0.30, "distribucion": 0.0}

RECOMENDACIONES_VEGETACION = {
    "EXCELENTE": (
        "Áreas verdes óptimas en la imagen.",
        "Proteger y mantener la vegetación existente.",
        "Considerar certificación de espacio verde sostenible.",
    ),
    "BUENA": (
        "Áreas verdes adecuadas.",
        "Mejorar la diversidad de especies.",
        "Conectar las áreas verdes entre sí para formar corredores.",
    ),
    "REGULAR": (
        "Cobertura verde insuficiente.",
        "Implementar un programa de reforestación.",
        "Crear áreas verdes comunitarias.",
        "Mejorar el mantenimiento de la vegetación existente.",
    ),
    "INSUFICIENTE": (
        "Déficit crítico de áreas verdes en la imagen.",
        "Priorizar la reforestación en la agenda urbana.",
        "Buscar apoyo de programas federales y locales.",
        "Involucrar a la comunidad en la conservación.",
    ),
}

# ---------------------------------------------------------------------------
# Índice visual de calidad del aire (estimación orientativa, NO es medición)
# ---------------------------------------------------------------------------
# Escalas para normalizar cada característica de la imagen a 0..1.
ESCALA_NITIDEZ = 800.0      # varianza del Laplaciano
ESCALA_CONTRASTE = 60.0     # desviación estándar en gris
ESCALA_BORDES = 0.05        # proporción de píxeles de borde (Canny)
ESCALA_SATURACION = 0.30    # saturación media 0..1

# Ajuste por temporada: en la CDMX la temporada seca (aprox. nov-abr) suele
# coincidir con peor calidad del aire. Es un supuesto simple, no un modelo.
AJUSTE_TEMPORADA_SECA = 1.3
MESES_TEMPORADA_SECA = (11, 12, 1, 2, 3, 4)

# ---------------------------------------------------------------------------
# Recompensas por ODS
# ---------------------------------------------------------------------------
NOMBRES_ODS = {
    "ods_3": "Salud y bienestar",
    "ods_11": "Ciudades y comunidades sostenibles",
}
PUNTOS_BASE_POR_ODS = {"ods_3": 30, "ods_11": 40}
BONO_MAXIMO_COBERTURA = 0.5   # el bono por cobertura verde llega hasta +50 %
PUNTOS_POR_NIVEL = 100

# ODS -> (contribuciones necesarias, nombre de la medalla)
MEDALLAS = {
    "ods_11": (15, "Guardián de las áreas verdes"),
}
