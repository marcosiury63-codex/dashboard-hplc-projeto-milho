import numpy as np
import pandas as pd
import pytest

from estatisticas import ANALITOS, faixa_acucares, preparar_replicas, resumir_leituras


def leituras(valores, tempo=24, grupo=1, analito="Etanol"):
    dados = pd.DataFrame({a: np.nan for a in ANALITOS}, index=range(len(valores)))
    dados[analito] = valores
    dados["Grupo"] = grupo
    dados["Tempo_h"] = tempo
    dados["Replica"] = range(1, len(valores) + 1)
    return dados


def test_dp_amostral_e_erro_relativo_da_triplicata():
    valores = [4.9419, 4.6412, 4.6874]
    ponto = resumir_leituras(leituras(valores), False).iloc[0]
    assert ponto["Etanol"] == pytest.approx(sum(valores) / 3)
    dp_esperado = (sum((v - sum(valores) / 3) ** 2 for v in valores) / 2) ** 0.5
    assert ponto["Etanol_dp"] == pytest.approx(dp_esperado)
    assert ponto["Etanol_erro_relativo"] == pytest.approx(100 * dp_esperado / ponto["Etanol"])
    assert ponto["Etanol_n"] == 3


def test_ausentes_nao_contam_como_zero_e_uma_leitura_nao_tem_dp():
    dados = leituras([1.0, 3.0, np.nan])
    dados["Frutose"] = [0.1, np.nan, np.nan]
    ponto = resumir_leituras(dados, False).iloc[0]
    assert ponto["Etanol"] == 2
    assert ponto["Etanol_n"] == 2
    assert ponto["Etanol_dp"] == pytest.approx(2 ** 0.5)
    assert ponto["Frutose_n"] == 1
    assert pd.isna(ponto["Frutose_dp"])
    assert pd.isna(ponto["Frutose_erro_relativo"])
    assert ponto["Acido_acetico_n"] == 0
    assert pd.isna(ponto["Acido_acetico"])


def test_zero_assumido_preserva_dados_e_nao_cria_triplicatas():
    dados = pd.concat([leituras([np.nan, np.nan], tempo=0), leituras([1, 2, 3])])
    original = dados.copy(deep=True)
    resumo = resumir_leituras(dados, True)
    zero = resumo.loc[resumo["Tempo_h"].eq(0)].iloc[0]
    assert zero["Etanol"] == zero["Etanol_dp"] == zero["Etanol_erro_relativo"] == 0
    assert zero["Etanol_n"] == 0
    assert "Zero assumido" in zero["Etanol_origem"]
    pd.testing.assert_frame_equal(dados, original)
    assert pd.isna(resumir_leituras(dados, False).iloc[0]["Etanol"])


def test_zero_experimental_real_nao_e_substituido():
    dados = leituras([0, 0, 0], tempo=0)
    ponto = resumir_leituras(dados, True).iloc[0]
    assert ponto["Etanol_n"] == 3
    assert ponto["Etanol_dp"] == 0
    assert pd.isna(ponto["Etanol_erro_relativo"])
    assert ponto["Etanol_origem"] == "Leituras HPLC"
    dados["Etanol"] = [0.1, 0.2, 0.3]
    assert resumir_leituras(dados, True).iloc[0]["Etanol"] == pytest.approx(0.2)


def test_curvas_individuais_comecam_em_zero_e_respeitam_filtro():
    dados = leituras([1, 2, 3])
    resumo = resumir_leituras(dados, True)
    base = preparar_replicas(dados, resumo, True)
    for _, serie in base.groupby("Replica"):
        assert serie["Tempo_h"].tolist() == [0, 24]
        assert serie.iloc[0]["Etanol"] == 0
        assert serie.iloc[0]["Etanol_n"] == 0
        assert serie.iloc[1]["Etanol_dp"] == 1
    sem_zero = preparar_replicas(dados, resumir_leituras(dados, False), False)
    assert not sem_zero["Tempo_h"].eq(0).any()


def test_escala_compartilhada_inclui_outro_acucar_e_suas_barras():
    dados = leituras([1, 1, 1], analito="DP4+")
    dados["Glicose"] = [2, 4, 6]
    dados["Frutose"] = [0.01, 0.02, 0.03]
    resumo = resumir_leituras(dados, False)
    inferior, superior = faixa_acucares(resumo)
    assert inferior == 0
    assert superior > 6  # Glicose: media 4 + DP 2, acima do DP4+.
