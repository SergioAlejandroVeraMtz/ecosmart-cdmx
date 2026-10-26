"""Progreso del usuario y recompensas por Objetivos de Desarrollo Sostenible (ODS).

Reglas de puntuación (definidas en config.py):
- ODS 11: puntos base * (1 + bono por cobertura verde, hasta +50 %).
- ODS 3: puntos base fijos por cada análisis documentado.
- Cada 100 puntos sube un nivel.
- Las medallas se otorgan una sola vez al alcanzar el número de contribuciones.

Las contribuciones guardan solo métricas escalares. Nunca guardan imágenes ni
arreglos, así que el archivo de progreso siempre es JSON válido.
"""

import json
from datetime import datetime
from pathlib import Path

import numpy as np

from . import config as cfg
from .io_seguro import a_tipos_json, escribir_json_atomico


def puntos_por_contribucion(ods, resumen):
    """Calcula los puntos que vale una contribución a partir de su resumen."""
    if ods not in cfg.PUNTOS_BASE_POR_ODS:
        raise ValueError(f"ODS no soportado: {ods}. Opciones: {', '.join(cfg.PUNTOS_BASE_POR_ODS)}")
    base = cfg.PUNTOS_BASE_POR_ODS[ods]
    if ods == "ods_11":
        cobertura = float(resumen.get("porcentaje_cobertura", 0.0))
        bono = min(cobertura / 100.0, cfg.BONO_MAXIMO_COBERTURA)
        return int(round(base * (1.0 + bono)))
    return int(base)


class Progreso:
    """Puntos, nivel, contribuciones y medallas de un usuario."""

    def __init__(self, usuario=cfg.USUARIO_POR_DEFECTO):
        self.usuario = usuario
        self.contribuciones = []
        self.medallas = []

    @property
    def puntos(self):
        return sum(int(c["puntos"]) for c in self.contribuciones)

    @property
    def nivel(self):
        return self.puntos // cfg.PUNTOS_POR_NIVEL + 1

    def contar(self, ods):
        return sum(1 for c in self.contribuciones if c["ods"] == ods)

    def registrar(self, ods, resumen, ahora=None):
        """Agrega una contribución. Devuelve (puntos ganados, medallas nuevas).

        `resumen` debe venir de ResultadoVegetacion.a_diccionario() (o de
        reportes.datos_para_progreso). Si contiene arreglos de NumPy, se rechaza.
        """
        for clave, valor in resumen.items():
            if isinstance(valor, np.ndarray):
                raise TypeError(f"El resumen contiene un arreglo en '{clave}'; usa a_diccionario()")
        puntos = puntos_por_contribucion(ods, resumen)
        marca = (ahora or datetime.now()).isoformat(timespec="seconds")
        self.contribuciones.append({
            "fecha": marca,
            "ods": ods,
            "puntos": puntos,
            "resumen": a_tipos_json(resumen),
        })
        return puntos, self._otorgar_medallas(ods)

    def _otorgar_medallas(self, ods):
        if ods not in cfg.MEDALLAS:
            return []
        necesarias, nombre = cfg.MEDALLAS[ods]
        if self.contar(ods) >= necesarias and nombre not in self.medallas:
            self.medallas.append(nombre)
            return [nombre]
        return []

    def a_diccionario(self):
        return {
            "version_esquema": cfg.VERSION_ESQUEMA,
            "usuario": self.usuario,
            "puntos": self.puntos,
            "nivel": self.nivel,
            "medallas": list(self.medallas),
            "contribuciones": a_tipos_json(self.contribuciones),
            "ultima_actualizacion": datetime.now().isoformat(timespec="seconds"),
        }

    def guardar(self, ruta):
        return escribir_json_atomico(self.a_diccionario(), ruta)

    @classmethod
    def cargar(cls, ruta, usuario_por_defecto=cfg.USUARIO_POR_DEFECTO):
        """Carga el progreso desde `ruta`.

        Devuelve (progreso, aviso). Si el archivo está dañado, se respalda con
        extensión .corrupto, se empieza de cero y el aviso lo explica. Nunca
        se borra información sin dejar copia.
        """
        ruta = Path(ruta)
        if not ruta.exists():
            return cls(usuario_por_defecto), None
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            if not isinstance(datos, dict) or not isinstance(datos.get("contribuciones", []), list):
                raise ValueError("estructura inesperada")
            progreso = cls(str(datos.get("usuario", usuario_por_defecto)))
            progreso.contribuciones = [c for c in datos.get("contribuciones", []) if isinstance(c, dict)]
            progreso.medallas = [str(m) for m in datos.get("medallas", [])]
            return progreso, None
        except (json.JSONDecodeError, ValueError, TypeError, OSError) as exc:
            respaldo = ruta.with_name(ruta.name + ".corrupto")
            try:
                ruta.replace(respaldo)
                detalle = f"Se respaldó en {respaldo.name}."
            except OSError:
                detalle = "No se pudo respaldar; revisa el archivo a mano."
            aviso = f"El progreso guardado estaba dañado ({exc}). Se empezó de cero. {detalle}"
            return cls(usuario_por_defecto), aviso
