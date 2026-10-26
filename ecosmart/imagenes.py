"""Carga, validación y generación de imágenes de prueba.

Las imágenes siempre se manejan en BGR (el orden de OpenCV) con uint8 y 3 canales.
Los escenarios sintéticos sirven para probar el sistema sin depender de fotos reales.
"""

from pathlib import Path

import cv2
import numpy as np

ESCENARIOS = ("parque", "urbano", "mixto", "contaminado")
EXTENSIONES_IMAGEN = (".jpg", ".jpeg", ".png", ".bmp")

COLOR_CIELO = (235, 206, 135)   # BGR, azul claro
COLOR_SUELO = (110, 115, 120)   # BGR, gris de asfalto (sin saturación)
COLOR_EDIFICIO = (150, 150, 150)
COLOR_BRUMA = (60, 90, 140)     # BGR, tono café que simula contaminación visible


def validar_imagen_bgr(imagen):
    """Lanza ValueError si la imagen no es un arreglo BGR de uint8 no vacío."""
    if not isinstance(imagen, np.ndarray):
        raise ValueError("La imagen debe ser un arreglo de NumPy")
    if imagen.ndim != 3 or imagen.shape[2] != 3:
        raise ValueError("Se esperaba una imagen a color de 3 canales (BGR)")
    if imagen.dtype != np.uint8:
        raise ValueError("La imagen debe tener tipo uint8")
    if imagen.size == 0:
        raise ValueError("La imagen está vacía")
    return imagen


def cargar_imagen(ruta):
    """Lee una imagen del disco en formato BGR."""
    ruta = Path(ruta)
    if not ruta.is_file():
        raise FileNotFoundError(f"No existe el archivo: {ruta}")
    if ruta.suffix.lower() not in EXTENSIONES_IMAGEN:
        raise ValueError(f"Formato no soportado: {ruta.suffix}. Usa {', '.join(EXTENSIONES_IMAGEN)}")
    imagen = cv2.imread(str(ruta), cv2.IMREAD_COLOR)
    if imagen is None:
        raise ValueError(f"No se pudo decodificar la imagen: {ruta.name}")
    return imagen


def redimensionar_maximo(imagen, lado_maximo=1024):
    """Reduce la imagen si su lado mayor supera `lado_maximo`, conservando la proporción."""
    alto, ancho = imagen.shape[:2]
    escala = min(1.0, lado_maximo / max(alto, ancho))
    if escala >= 1.0:
        return imagen
    nuevo = (int(ancho * escala), int(alto * escala))
    return cv2.resize(imagen, nuevo, interpolation=cv2.INTER_AREA)


def _manchas_verdes(imagen, rng, cantidad, radio_min, radio_max, zona):
    """Dibuja círculos de color verde en la franja vertical `zona` (y0, y1)."""
    y0, y1 = zona
    for _ in range(cantidad):
        centro = (int(rng.integers(0, imagen.shape[1])), int(rng.integers(y0, y1)))
        radio = int(rng.integers(radio_min, radio_max + 1))
        color = (int(rng.integers(30, 61)), int(rng.integers(130, 191)), int(rng.integers(30, 61)))
        cv2.circle(imagen, centro, radio, color, -1)


def _edificios(imagen, rng, cantidad, zona):
    """Dibuja rectángulos grises que simulan edificios."""
    y0, y1 = zona
    for _ in range(cantidad):
        x0 = int(rng.integers(0, imagen.shape[1] - 40))
        y_top = int(rng.integers(y0, y1 - 30))
        ancho = int(rng.integers(30, 90))
        alto = int(rng.integers(40, 140))
        cv2.rectangle(imagen, (x0, y_top), (x0 + ancho, min(y_top + alto, y1)), COLOR_EDIFICIO, -1)


def generar_escenario(nombre, alto=600, ancho=400, semilla=42):
    """Crea una imagen sintética de un escenario conocido.

    Con la misma semilla el resultado siempre es idéntico, lo que permite
    comparar versiones del código sin variaciones aleatorias.

    - parque: mucha vegetación
    - urbano: edificios y poco verde
    - mixto: edificios con árboles dispersos
    - contaminado: sin vegetación y con bruma visible
    """
    if nombre not in ESCENARIOS:
        raise ValueError(f"Escenario desconocido: {nombre}. Opciones: {', '.join(ESCENARIOS)}")

    rng = np.random.default_rng(semilla)
    imagen = np.empty((alto, ancho, 3), np.uint8)
    limite = alto // 3
    imagen[:limite] = COLOR_CIELO
    imagen[limite:] = COLOR_SUELO
    franja = (limite, alto)

    if nombre == "parque":
        _manchas_verdes(imagen, rng, cantidad=25, radio_min=25, radio_max=50, zona=franja)
    elif nombre == "urbano":
        _edificios(imagen, rng, cantidad=8, zona=franja)
        _manchas_verdes(imagen, rng, cantidad=3, radio_min=10, radio_max=18, zona=franja)
    elif nombre == "mixto":
        _edificios(imagen, rng, cantidad=5, zona=franja)
        _manchas_verdes(imagen, rng, cantidad=10, radio_min=15, radio_max=35, zona=franja)
    else:  # contaminado
        _edificios(imagen, rng, cantidad=6, zona=franja)
        cv2.rectangle(imagen, (0, limite), (ancho, alto), COLOR_BRUMA, -1)
        cv2.rectangle(imagen, (0, limite), (ancho, limite + 60), COLOR_BRUMA, -1)
    return imagen
