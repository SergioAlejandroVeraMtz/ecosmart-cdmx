"""Línea de comandos de EcoSmart.

Ejemplos:
    python -m ecosmart analizar foto.jpg --usuario sergio --json reporte.json
    python -m ecosmart analizar foto.jpg --registrar --ods ods_11
    python -m ecosmart escenario parque --salida parque.png
    python -m ecosmart lote carpeta_fotos --csv resultados.csv
    python -m ecosmart gui
"""

import argparse
import sys
from pathlib import Path

import cv2

from . import aire, configuracion, config as cfg, graficos, imagenes, lote
from . import recompensas, reportes, vegetacion


def _analizar(imagen, mes=None):
    imagen = imagenes.redimensionar_maximo(imagen)
    return vegetacion.analizar(imagen), aire.estimar(imagen, mes=mes)


def cmd_analizar(args):
    imagen = imagenes.cargar_imagen(args.ruta)
    veg, air = _analizar(imagen, mes=args.mes)
    reporte = reportes.construir_reporte(args.usuario, veg, air)
    print(reportes.resumen_texto(reporte))

    if args.json:
        reportes.guardar_reporte(reporte, args.json)
        print(f"\nReporte JSON: {args.json}")
    if args.mascara:
        reportes.guardar_mascara(veg.mascara, args.mascara)
        print(f"Máscara: {args.mascara}")
    if args.superposicion:
        graficos.guardar_figura(graficos.figura_resumen(imagen, veg), args.superposicion)
        print(f"Gráfica: {args.superposicion}")
    if args.registrar:
        progreso, aviso = recompensas.Progreso.cargar(args.progreso, args.usuario)
        if aviso:
            print(f"Aviso: {aviso}")
        progreso.usuario = args.usuario
        puntos, nuevas = progreso.registrar(args.ods, reportes.datos_para_progreso(veg, air))
        progreso.guardar(args.progreso)
        print(f"\nSe registraron {puntos} puntos ({args.ods}). Total: {progreso.puntos}, nivel {progreso.nivel}.")
        for medalla in nuevas:
            print(f"Medalla nueva: {medalla}")
    return 0


def cmd_escenario(args):
    imagen = imagenes.generar_escenario(args.nombre, semilla=args.semilla)
    veg, air = _analizar(imagen)
    print(f"Escenario '{args.nombre}': cobertura {veg.porcentaje_cobertura:.2f} % ({veg.evaluacion}), "
          f"aire orientativo {air.indice} ({air.categoria})")
    if args.salida:
        if not cv2.imwrite(str(args.salida), imagen):
            raise OSError(f"No se pudo escribir {args.salida}")
        print(f"Imagen: {args.salida}")
    return 0


def cmd_lote(args):
    resultado = lote.analizar_carpeta(args.carpeta, args.csv, mes=args.mes)
    print(f"Imágenes procesadas: {resultado['procesadas']}")
    print(f"Cobertura promedio: {lote.promedio_cobertura(resultado['filas'])} %")
    print(f"CSV: {resultado['csv']}")
    for error in resultado["errores"]:
        print(f"Error en {error['archivo']}: {error['motivo']}", file=sys.stderr)
    return 0 if not resultado["errores"] else 1


def cmd_configuracion(args):
    parametros = configuracion.cargar(args.archivo)
    aplicados = configuracion.aplicar(parametros)
    print(f"Parámetros aplicados desde {args.archivo}: {aplicados or 'ninguno'}")
    return 0


def cmd_gui(_args):
    import tkinter as tk

    from .gui import EcoSmartApp

    raiz = tk.Tk()
    EcoSmartApp(raiz)
    raiz.mainloop()
    return 0


def construir_parser():
    parser = argparse.ArgumentParser(prog="ecosmart", description=cfg.NOMBRE_APP)
    parser.add_argument("--config", type=Path, help="Archivo JSON con parámetros personalizados")
    sub = parser.add_subparsers(dest="comando")

    p = sub.add_parser("analizar", help="Analiza una imagen")
    p.add_argument("ruta", type=Path)
    p.add_argument("--usuario", default=cfg.USUARIO_POR_DEFECTO)
    p.add_argument("--mes", type=int, choices=range(1, 13), metavar="1-12", help="Mes para el ajuste de temporada")
    p.add_argument("--json", type=Path, help="Guardar reporte en JSON")
    p.add_argument("--mascara", type=Path, help="Guardar máscara de vegetación en PNG")
    p.add_argument("--superposicion", type=Path, help="Guardar gráfica resumen en PNG")
    p.add_argument("--registrar", action="store_true", help="Registrar la contribución en el progreso")
    p.add_argument("--ods", default="ods_11", choices=sorted(cfg.PUNTOS_BASE_POR_ODS))
    p.add_argument("--progreso", type=Path, default=cfg.DIRECTORIO_DATOS / cfg.NOMBRE_ARCHIVO_PROGRESO)
    p.set_defaults(func=cmd_analizar)

    p = sub.add_parser("escenario", help="Genera y analiza un escenario de prueba")
    p.add_argument("nombre", choices=imagenes.ESCENARIOS)
    p.add_argument("--semilla", type=int, default=42)
    p.add_argument("--salida", type=Path, help="Guardar la imagen generada")
    p.set_defaults(func=cmd_escenario)

    p = sub.add_parser("lote", help="Analiza todas las imágenes de una carpeta")
    p.add_argument("carpeta", type=Path)
    p.add_argument("--csv", type=Path, default=Path("resultados.csv"))
    p.add_argument("--mes", type=int, choices=range(1, 13), metavar="1-12")
    p.set_defaults(func=cmd_lote)

    p = sub.add_parser("configuracion", help="Valida y muestra un archivo de parámetros")
    p.add_argument("archivo", type=Path)
    p.set_defaults(func=cmd_configuracion)

    p = sub.add_parser("gui", help="Abre la interfaz gráfica")
    p.set_defaults(func=cmd_gui)
    return parser


def main(argv=None):
    parser = construir_parser()
    args = parser.parse_args(argv)
    if not args.comando:
        parser.print_help()
        return 1
    try:
        if args.config:
            configuracion.aplicar(configuracion.cargar(args.config))
        return args.func(args)
    except (FileNotFoundError, NotADirectoryError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
