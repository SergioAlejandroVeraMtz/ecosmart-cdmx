import numpy as np
import pytest

from ecosmart import aire, config as cfg, imagenes


@pytest.mark.parametrize("nombre", imagenes.ESCENARIOS)
def test_indice_de_aire_esta_en_rango(nombre):
    resultado = aire.estimar(imagenes.generar_escenario(nombre), mes=7)
    assert 0.0 <= resultado.indice <= 200.0
    assert resultado.categoria in {nombre_banda for _, nombre_banda in aire.BANDAS}


@pytest.mark.parametrize(
    "indice, categoria",
    [(0.0, "Buena"), (50.0, "Buena"), (51.0, "Regular"), (120.0, "Mala"), (180.0, "Muy mala"), (200.0, "Muy mala")],
)
def test_categorias_siguen_las_bandas(indice, categoria):
    assert aire.categoria_para(indice) == categoria


def test_temporada_seca_aumenta_el_indice():
    imagen = imagenes.generar_escenario("urbano")
    verano = aire.estimar(imagen, mes=7)
    invierno = aire.estimar(imagen, mes=1)
    assert verano.ajuste_temporada == 1.0
    assert invierno.ajuste_temporada == cfg.AJUSTE_TEMPORADA_SECA
    assert invierno.indice >= verano.indice


def test_el_indice_nunca_pasa_de_200():
    gris_ruidoso = np.random.default_rng(0).integers(0, 256, (200, 200, 3), dtype=np.uint8)
    resultado = aire.estimar(gris_ruidoso, mes=1)
    assert resultado.indice <= 200.0


def test_confianza_siempre_es_baja():
    resultado = aire.estimar(imagenes.generar_escenario("parque"), mes=5)
    assert resultado.confianza == aire.CONFIANZA_BAJA


def test_a_diccionario_es_serializable():
    import json

    json.dumps(aire.estimar(imagenes.generar_escenario("mixto"), mes=3).a_diccionario())


def test_generar_escenario_es_determinista():
    a = imagenes.generar_escenario("parque", semilla=7)
    b = imagenes.generar_escenario("parque", semilla=7)
    c = imagenes.generar_escenario("parque", semilla=8)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_escenario_desconocido_es_error():
    with pytest.raises(ValueError):
        imagenes.generar_escenario("playa")


def test_validar_imagen_rechaza_formas_incorrectas():
    with pytest.raises(ValueError):
        imagenes.validar_imagen_bgr(np.zeros((10, 10), np.uint8))
    with pytest.raises(ValueError):
        imagenes.validar_imagen_bgr(np.zeros((10, 10, 3), np.float32))
    with pytest.raises(ValueError):
        imagenes.validar_imagen_bgr("no es una imagen")


def test_redimensionar_respeta_proporcion():
    grande = np.zeros((2000, 1000, 3), np.uint8)
    pequena = imagenes.redimensionar_maximo(grande, lado_maximo=500)
    alto, ancho = pequena.shape[:2]
    assert max(alto, ancho) == 500
    assert abs(alto / ancho - 2.0) < 0.01


def test_redimensionar_no_agranda():
    pequena = np.zeros((100, 80, 3), np.uint8)
    assert imagenes.redimensionar_maximo(pequena, lado_maximo=1024) is pequena


def test_cargar_imagen_inexistente_es_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        imagenes.cargar_imagen(tmp_path / "nada.jpg")


def test_cargar_formato_no_soportado_es_error(tmp_path):
    ruta = tmp_path / "archivo.txt"
    ruta.write_text("hola", encoding="utf-8")
    with pytest.raises(ValueError):
        imagenes.cargar_imagen(ruta)
