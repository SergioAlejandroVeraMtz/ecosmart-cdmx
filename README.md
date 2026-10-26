# EcoSmart CDMX

Herramienta de análisis visual de áreas verdes y una estimación orientativa de
calidad del aire, con un sistema de progreso por Objetivos de Desarrollo
Sostenible (ODS 3 y ODS 11).

Proyecto de la materia **Procesamiento de Imágenes Digitales** (IPN, ESCOM, grupo 3BM1).

## Qué hace

- **Cobertura verde:** segmenta la vegetación en HSV, limpia la máscara con
  morfología y mide porcentaje, número de áreas, tamaños, distribución por
  cuadrantes, saturación media (vigor) y el índice Excess Green.
- **Evaluación:** clasifica la cobertura como EXCELENTE, BUENA, REGULAR o
  INSUFICIENTE, con recomendaciones.
- **Índice visual de aire:** estimación orientativa a partir de nitidez,
  contraste, bordes y saturación. Categorías según las bandas IMECA.
- **Progreso ODS:** puntos, niveles y medallas, guardados en JSON.
- **Procesamiento por lote:** analiza una carpeta completa y exporta CSV.
- **Interfaz gráfica** (Tkinter) con gráficas, progreso y reportes.
- **Línea de comandos** para usar todo sin abrir la ventana.

## Limitaciones (léelas antes de presentar resultados)

- La **cobertura** se mide sobre la imagen. No equivale a superficie real del
  terreno: depende del encuadre, la hora y la cámara.
- La **"salud" es la saturación media del verde**, un proxy de vigor. **No es
  NDVI**, que necesita una banda infrarroja que una foto de celular no tiene.
- El **índice de aire no es una medición**. Los pesos y escalas son supuestos
  sin calibrar. Para datos oficiales usa la red **SIMAT** de la CDMX.
- El ajuste de temporada seca (×1.3 en noviembre-abril) es un supuesto simple.
- Los escenarios de prueba son **sintéticos**: sirven para verificar el
  código, no para medir la ciudad.

## Instalación

Requiere Python 3.10 o superior.

```bash
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

En macOS con Anaconda, instala las dependencias en el mismo intérprete que
usas para ejecutar el programa, por ejemplo:
`/opt/anaconda3/bin/python -m pip install -r requirements.txt`.

## Uso

```bash
# Interfaz gráfica
python -m ecosmart gui

# Analizar una foto y guardar reporte, máscara y gráfica
python -m ecosmart analizar foto.jpg --usuario mi_usuario --json reporte.json \
    --mascara mascara.png --superposicion grafica.png

# Analizar y sumar la contribución al progreso
python -m ecosmart analizar foto.jpg --registrar --ods ods_11

# Escenario de prueba
python -m ecosmart escenario contaminado --salida contaminado.png

# Carpeta completa a CSV
python -m ecosmart lote carpeta_fotos --csv resultados.csv --mes 3

# Parámetros personalizados (ver abajo)
python -m ecosmart --config ecosmart.json analizar foto.jpg
```

## Configuración personalizada

Crea un archivo `ecosmart.json` con los parámetros que quieras cambiar. Solo se
aceptan claves conocidas y valores dentro de rango:

```json
{"GAMMA_ILUMINACION": 1.4, "AJUSTE_TEMPORADA_SECA": 1.2}
```

Parámetros disponibles y sus valores por defecto están en `ecosmart/config.py`.

## Pruebas

```bash
pip install pytest
python -m pytest -q
```

Las pruebas cubren la segmentación, la evaluación por umbrales, el progreso
(incluido el guardado seguro y la recuperación de archivos dañados), los
reportes, el lote, la línea de comandos y la configuración.

## Estructura

```
ecosmart/
  config.py          parámetros y umbrales
  imagenes.py        carga, validación y escenarios sintéticos
  vegetacion.py      segmentación y métricas de áreas verdes
  aire.py            índice visual orientativo de aire
  recompensas.py     puntos, niveles y medallas
  io_seguro.py       JSON seguro y escritura atómica
  reportes.py        reportes, texto, máscaras y superposiciones
  graficos.py        figuras de matplotlib
  lote.py            análisis de carpetas y CSV
  configuracion.py   carga y validación de parámetros
  cli.py             línea de comandos
  gui.py             interfaz gráfica
tests/               pruebas automáticas
```

## Historial de cambios

**2.0.0**
- Corrección del JSON inválido: las matrices de NumPy ya no se guardan y la
  escritura es atómica.
- Corrección gamma de 0.8 a 1.25: los verdes oscuros ya no desaparecen.
- Escenario "contaminado" realista (sin vegetación y con bruma).
- Eliminado el cálculo de NDVI simulado; ahora se llama "saturación media".
- Cobertura de la distribución espacial: 0 cuando no hay vegetación.
- Índice de aire presentado como estimación orientativa, con su confianza.
- Módulos separados, línea de comandos, procesamiento por lote, gráficas y pruebas.

## Créditos

Desarrollado por Sergio Alejandro Vera Martínez. Trabajo de la materia Procesamiento
de Imágenes Digitales, IPN - ESCOM, grupo 3BM1.
