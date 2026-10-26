import json
from datetime import datetime

import numpy as np
import pytest

from ecosmart import config as cfg
from ecosmart import recompensas, vegetacion


def resumen_base(cobertura=20.0):
    return {"porcentaje_cobertura": cobertura, "categoria_aire": "Buena"}


def test_puntos_ods_11_con_bono_por_cobertura():
    assert recompensas.puntos_por_contribucion("ods_11", resumen_base(0.0)) == 40
    assert recompensas.puntos_por_contribucion("ods_11", resumen_base(20.0)) == 48
    # El bono se topa en +50 %, así que 90 % y 100 % valen lo mismo.
    assert recompensas.puntos_por_contribucion("ods_11", resumen_base(90.0)) == 60
    assert recompensas.puntos_por_contribucion("ods_11", resumen_base(100.0)) == 60


def test_puntos_ods_3_son_fijos():
    assert recompensas.puntos_por_contribucion("ods_3", resumen_base(55.0)) == cfg.PUNTOS_BASE_POR_ODS["ods_3"]


def test_ods_desconocido_es_error():
    with pytest.raises(ValueError):
        recompensas.puntos_por_contribucion("ods_99", resumen_base())


def test_registrar_suma_puntos_y_nivel():
    progreso = recompensas.Progreso("tester")
    ganados, _ = progreso.registrar("ods_11", resumen_base(20.0))
    assert ganados == 48
    assert progreso.puntos == 48
    assert progreso.nivel == 1
    progreso.registrar("ods_11", resumen_base(20.0))
    assert progreso.nivel == 1 + 96 // cfg.PUNTOS_POR_NIVEL


def test_rechaza_arreglos_de_numpy_en_el_resumen():
    progreso = recompensas.Progreso("tester")
    con_mascara = dict(resumen_base(), mascara_verde=np.zeros((2, 2), np.uint8))
    with pytest.raises(TypeError):
        progreso.registrar("ods_11", con_mascara)
    assert progreso.contribuciones == []


def test_medalla_se_otorga_una_sola_vez():
    progreso = recompensas.Progreso("tester")
    necesarias, nombre = cfg.MEDALLAS["ods_11"]
    nuevas_totales = []
    for _ in range(necesarias + 3):
        _, nuevas = progreso.registrar("ods_11", resumen_base())
        nuevas_totales.extend(nuevas)
    assert nuevas_totales == [nombre]
    assert progreso.medallas == [nombre]


def test_guardado_y_carga_ida_y_vuelta(tmp_path):
    ruta = tmp_path / "progreso.json"
    progreso = recompensas.Progreso("tester")
    progreso.registrar("ods_11", resumen_base(30.0), ahora=datetime(2026, 10, 25, 22, 0))
    progreso.guardar(ruta)

    cargado, aviso = recompensas.Progreso.cargar(ruta)
    assert aviso is None
    assert cargado.usuario == "tester"
    assert cargado.puntos == progreso.puntos
    assert cargado.contribuciones[0]["fecha"] == "2026-10-25T22:00:00"


def test_archivo_guardado_es_json_valido_con_arreglos_en_el_resumen(tmp_path):
    """Regresión del error original: el JSON quedaba cortado por una matriz de NumPy."""
    ruta = tmp_path / "progreso.json"
    veg = vegetacion.analizar(np.full((60, 40, 3), (60, 180, 60), np.uint8))
    progreso = recompensas.Progreso("tester")
    progreso.registrar("ods_11", veg.a_diccionario())
    progreso.guardar(ruta)
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert datos["puntos"] == progreso.puntos
    assert "mascara_verde" not in json.dumps(datos)


def test_archivo_corrupto_se_respalda_y_no_se_pierde(tmp_path):
    ruta = tmp_path / "progreso.json"
    ruta.write_text('{"puntos": 10, "contribuciones": [', encoding="utf-8")
    progreso, aviso = recompensas.Progreso.cargar(ruta, "tester")
    assert progreso.puntos == 0
    assert aviso is not None and "respaldó" in aviso
    assert (tmp_path / "progreso.json.corrupto").exists()
    assert not ruta.exists()


def test_archivo_inexistente_da_progreso_nuevo(tmp_path):
    progreso, aviso = recompensas.Progreso.cargar(tmp_path / "no_existe.json", "nuevo")
    assert progreso.usuario == "nuevo"
    assert progreso.contribuciones == []
    assert aviso is None
