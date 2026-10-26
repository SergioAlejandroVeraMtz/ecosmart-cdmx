import numpy as np
import pytest

from ecosmart import config as cfg
from ecosmart import imagenes, vegetacion


def test_verde_solido_tiene_cobertura_completa(verde_claro):
    resultado = vegetacion.analizar(verde_claro)
    assert resultado.porcentaje_cobertura == pytest.approx(100.0)
    assert resultado.numero_areas == 1


def test_cielo_no_tiene_vegetacion(cielo):
    resultado = vegetacion.analizar(cielo)
    assert resultado.porcentaje_cobertura == 0.0
    assert resultado.numero_areas == 0
    assert resultado.evaluacion == "INSUFICIENTE"
    assert resultado.coeficiente_distribucion == 0.0


def test_verde_oscuro_se_detecta_con_gamma_nuevo():
    """Regresión: con gamma 0.8 un parche G=45 se perdía; con 1.25 debe detectarse."""
    parche = np.zeros((600, 400, 3), np.uint8)
    parche[80:120, 150:250] = (0, 45, 0)
    resultado = vegetacion.analizar(parche)
    assert resultado.pixeles_verdes == 4000


def test_gamma_menor_a_uno_pierde_verde_oscuro():
    """Documenta por qué se cambió el gamma: con 0.8 el mismo parche desaparece."""
    parche = np.zeros((600, 400, 3), np.uint8)
    parche[80:120, 150:250] = (0, 45, 0)
    procesada = vegetacion.corregir_iluminacion(parche, gamma=0.8)
    mascara = vegetacion.segmentar_vegetacion(procesada)
    assert np.count_nonzero(mascara) == 0


def test_gamma_no_positivo_es_error(verde_claro):
    with pytest.raises(ValueError):
        vegetacion.corregir_iluminacion(verde_claro, gamma=0)


def test_kernel_par_se_corrige_a_impar(verde_claro):
    cfg.TAMANO_KERNEL = 4
    kernel = vegetacion._kernel()
    assert kernel.shape == (5, 5)
    assert vegetacion.analizar(verde_claro).porcentaje_cobertura == pytest.approx(100.0)


def test_parque_tiene_mas_cobertura_que_urbano():
    parque = vegetacion.analizar(imagenes.generar_escenario("parque"))
    urbano = vegetacion.analizar(imagenes.generar_escenario("urbano"))
    assert parque.porcentaje_cobertura > urbano.porcentaje_cobertura
    assert parque.porcentaje_cobertura > 10.0


def test_escenario_contaminado_es_insuficiente():
    resultado = vegetacion.analizar(imagenes.generar_escenario("contaminado"))
    assert resultado.evaluacion == "INSUFICIENTE"
    assert resultado.porcentaje_cobertura < 1.0


def test_coeficiente_uniforme_es_maximo():
    uniforme = [25.0, 25.0, 25.0, 25.0]
    desigual = [100.0, 0.0, 0.0, 0.0]
    assert vegetacion.coeficiente_distribucion(uniforme) == pytest.approx(1.0)
    assert vegetacion.coeficiente_distribucion(desigual) < vegetacion.coeficiente_distribucion(uniforme)


def test_coeficiente_sin_verde_es_cero():
    assert vegetacion.coeficiente_distribucion([0.0, 0.0, 0.0, 0.0]) == 0.0


@pytest.mark.parametrize(
    "cobertura, saturacion, distribucion, esperado",
    [
        (35.0, 0.80, 0.70, "EXCELENTE"),
        (25.0, 0.60, 0.50, "BUENA"),
        (12.0, 0.40, 0.10, "REGULAR"),
        (35.0, 0.20, 0.90, "INSUFICIENTE"),  # saturación < 0.30 no alcanza REGULAR
        (0.0, 0.0, 0.0, "INSUFICIENTE"),
    ],
)
def test_evaluar_respeta_umbrales(cobertura, saturacion, distribucion, esperado):
    assert vegetacion.evaluar(cobertura, saturacion, distribucion) == esperado


def test_a_diccionario_no_incluye_mascara_y_es_serializable(verde_claro):
    import json

    datos = vegetacion.analizar(verde_claro).a_diccionario()
    assert "mascara" not in datos
    json.dumps(datos)  # no debe lanzar excepción


def test_entrada_invalida_lanza_error():
    gris = np.zeros((50, 50), np.uint8)
    with pytest.raises(ValueError):
        vegetacion.analizar(gris)
    with pytest.raises(ValueError):
        vegetacion.analizar(np.zeros((0, 0, 3), np.uint8))


def test_exg_positivo_para_verde_y_cero_sin_verde(verde_claro, cielo):
    mascara_verde = np.full(verde_claro.shape[:2], 255, np.uint8)
    assert vegetacion.indice_exg_medio(verde_claro, mascara_verde) > 0
    assert vegetacion.indice_exg_medio(cielo, np.zeros(cielo.shape[:2], np.uint8)) == 0.0
