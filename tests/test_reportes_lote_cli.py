import json

import cv2
import numpy as np
import pytest

from ecosmart import cli, configuracion, graficos, imagenes, io_seguro, lote, reportes, vegetacion
from ecosmart import aire, recompensas
from ecosmart import config as cfg


def test_a_tipos_json_descarta_arreglos_y_convierte_escalares():
    datos = {"a": np.float64(1.5), "b": np.int64(3), "c": np.zeros(3), "d": [np.int32(2), np.zeros(2)], "e": float("nan")}
    limpio = io_seguro.a_tipos_json(datos)
    assert "c" not in limpio
    assert limpio["a"] == 1.5 and isinstance(limpio["a"], float)
    assert limpio["b"] == 3 and isinstance(limpio["b"], int)
    assert limpio["d"] == [2]
    assert limpio["e"] is None
    json.dumps(limpio, allow_nan=False)


def test_escritura_atomica_no_deja_temporales(tmp_path):
    ruta = tmp_path / "datos.json"
    io_seguro.escribir_json_atomico({"x": 1}, ruta)
    io_seguro.escribir_json_atomico({"x": 2}, ruta)
    assert json.loads(ruta.read_text(encoding="utf-8")) == {"x": 2}
    assert [p.name for p in tmp_path.iterdir()] == ["datos.json"]


def test_fallo_al_escribir_conserva_el_archivo_anterior(tmp_path, monkeypatch):
    ruta = tmp_path / "datos.json"
    io_seguro.escribir_json_atomico({"version": "buena"}, ruta)

    def explota(*_args, **_kwargs):
        raise RuntimeError("fallo simulado")

    monkeypatch.setattr(io_seguro.json, "dumps", explota)
    with pytest.raises(RuntimeError):
        io_seguro.escribir_json_atomico({"version": "mala"}, ruta)
    assert json.loads(ruta.read_text(encoding="utf-8")) == {"version": "buena"}
    assert [p.name for p in tmp_path.iterdir()] == ["datos.json"]


def test_reporte_completo_es_json_valido(tmp_path):
    imagen = imagenes.generar_escenario("mixto")
    veg = vegetacion.analizar(imagen)
    air = aire.estimar(imagen, mes=4)
    reporte = reportes.construir_reporte("tester", veg, air)
    ruta = reportes.guardar_reporte(reporte, tmp_path / "reporte.json")
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert datos["usuario"] == "tester"
    assert datos["vegetacion"]["evaluacion"] == veg.evaluacion
    assert "mascara" not in datos["vegetacion"]
    assert "aviso" in datos


def test_resumen_texto_incluye_avisos_y_recomendaciones():
    imagen = imagenes.generar_escenario("contaminado")
    veg = vegetacion.analizar(imagen)
    texto = reportes.resumen_texto(reportes.construir_reporte("t", veg, aire.estimar(imagen, mes=6)))
    assert "INSUFICIENTE" in texto
    assert "orientativos" in texto
    assert "Recomendaciones:" in texto


def test_superposicion_pinta_solo_la_vegetacion(verde_claro, cielo):
    mascara = np.zeros(cielo.shape[:2], np.uint8)
    mascara[:100, :100] = 255
    resultado = reportes.superponer(cielo, mascara)
    assert resultado.shape == cielo.shape
    assert not np.array_equal(resultado[:100, :100], cielo[:100, :100])
    assert np.array_equal(resultado[200:, 200:], cielo[200:, 200:])


def test_guardar_mascara_escribe_png(tmp_path):
    veg = vegetacion.analizar(imagenes.generar_escenario("parque"))
    ruta = reportes.guardar_mascara(veg.mascara, tmp_path / "mascara.png")
    leida = cv2.imread(str(ruta), cv2.IMREAD_GRAYSCALE)
    assert leida.shape == veg.mascara.shape


def test_lote_procesa_carpeta_y_reporta_errores(tmp_path):
    carpeta = tmp_path / "fotos"
    carpeta.mkdir()
    cv2.imwrite(str(carpeta / "parque.png"), imagenes.generar_escenario("parque"))
    cv2.imwrite(str(carpeta / "urbano.png"), imagenes.generar_escenario("urbano"))
    (carpeta / "roto.jpg").write_bytes(b"no es una imagen")
    (carpeta / "notas.txt").write_text("ignorar", encoding="utf-8")

    resultado = lote.analizar_carpeta(carpeta, tmp_path / "resultados.csv", mes=5)
    assert resultado["procesadas"] == 2
    assert [e["archivo"] for e in resultado["errores"]] == ["roto.jpg"]
    assert resultado["filas"][0]["archivo"] == "parque.png"
    csv_texto = (tmp_path / "resultados.csv").read_text(encoding="utf-8-sig")
    assert csv_texto.splitlines()[0].split(",") == list(lote.CAMPOS_CSV)


def test_lote_con_carpeta_inexistente_es_error(tmp_path):
    with pytest.raises(NotADirectoryError):
        lote.listar_imagenes(tmp_path / "no_hay")


def test_promedio_cobertura_de_lista_vacia_es_cero():
    assert lote.promedio_cobertura([]) == 0.0


def test_figuras_se_generan_y_guardan(tmp_path):
    imagen = imagenes.generar_escenario("parque")
    veg = vegetacion.analizar(imagen)
    for figura in (graficos.figura_resumen(imagen, veg), graficos.figura_tonos(imagen, veg),
                   graficos.figura_superposicion(imagen, veg)):
        graficos.guardar_figura(figura, tmp_path / f"f{id(figura)}.png")
    assert len(list(tmp_path.glob("*.png"))) == 3


def test_configuracion_valida_y_aplica(tmp_path):
    ruta = tmp_path / "ecosmart.json"
    ruta.write_text(json.dumps({"GAMMA_ILUMINACION": 1.4, "TAMANO_KERNEL": 7}), encoding="utf-8")
    parametros = configuracion.cargar(ruta)
    configuracion.aplicar(parametros)
    assert cfg.GAMMA_ILUMINACION == 1.4
    assert cfg.TAMANO_KERNEL == 7


@pytest.mark.parametrize(
    "contenido",
    [
        {"GAMMA_INEXISTENTE": 1.0},
        {"GAMMA_ILUMINACION": 99.0},
        {"GAMMA_ILUMINACION": "uno"},
        {"GAMMA_ILUMINACION": True},
        ["lista", "no", "valida"],
    ],
)
def test_configuracion_rechaza_valores_invalidos(contenido):
    with pytest.raises(ValueError):
        configuracion.validar(contenido)


def test_configuracion_inexistente_es_vacia(tmp_path):
    assert configuracion.cargar(tmp_path / "no_existe.json") == {}


def test_cli_analizar_registra_y_guarda_reporte(tmp_path, capsys):
    imagen_ruta = tmp_path / "parque.png"
    cv2.imwrite(str(imagen_ruta), imagenes.generar_escenario("parque"))
    progreso = tmp_path / "progreso.json"
    reporte = tmp_path / "reporte.json"

    codigo = cli.main(["analizar", str(imagen_ruta), "--usuario", "tester", "--json", str(reporte),
                       "--registrar", "--ods", "ods_11", "--progreso", str(progreso), "--mes", "7"])
    assert codigo == 0
    assert json.loads(reporte.read_text(encoding="utf-8"))["usuario"] == "tester"
    datos = json.loads(progreso.read_text(encoding="utf-8"))
    assert datos["puntos"] > 0
    assert "Cobertura verde" in capsys.readouterr().out


def test_cli_error_de_archivo_regresa_codigo_2(tmp_path, capsys):
    codigo = cli.main(["analizar", str(tmp_path / "no_existe.jpg")])
    assert codigo == 2
    assert "Error:" in capsys.readouterr().err


def test_cli_escenario_con_salida(tmp_path):
    salida = tmp_path / "urbano.png"
    assert cli.main(["escenario", "urbano", "--salida", str(salida)]) == 0
    assert salida.exists()


def test_cli_sin_comando_muestra_ayuda():
    assert cli.main([]) == 1


def test_progreso_cargar_y_registrar_desde_cli(tmp_path):
    progreso = recompensas.Progreso("x")
    progreso.registrar("ods_3", {"categoria_aire": "Buena"})
    ruta = tmp_path / "p.json"
    progreso.guardar(ruta)
    cargado, _ = recompensas.Progreso.cargar(ruta)
    assert cargado.puntos == cfg.PUNTOS_BASE_POR_ODS["ods_3"]
