import base64
import json
from pathlib import Path
from statistics import stdev

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest


def array_plotly(valores):
    if isinstance(valores, dict) and "bdata" in valores:
        return np.frombuffer(base64.b64decode(valores["bdata"]), dtype=valores["dtype"])
    return np.asarray(valores)


def figuras(app):
    assert not app.exception, [e.message for e in app.exception]
    return [json.loads(chart.proto.spec) for chart in app.get("plotly_chart")]


def test_graficos_estatisticas_filtros_e_replicas():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=30).run()
    charts = figuras(app)
    assert len(charts) == 5
    for chart in charts:
        assert chart["layout"]["hovermode"] == "closest"
        assert chart["layout"]["hoverlabel"]["bgcolor"] == "#17171d"
        assert chart["layout"]["hoverlabel"]["font"]["color"] == "#f5f5f7"
        for serie in chart["data"]:
            assert serie["error_y"]["visible"]
            assert "Erro relativo:" in serie["hovertemplate"]
            assert "Média ± DP:" in serie["hovertemplate"]
            assert serie["hovertemplate"].endswith("<extra></extra>")
    for serie in charts[0]["data"]:
        assert array_plotly(serie["x"])[0] == array_plotly(serie["y"])[0] == 0
        assert array_plotly(serie["error_y"]["array"])[0] == 0
    dados = app.dataframe[0].value
    assert dados.loc[dados["Tempo_h"].eq(0), "Etanol"].isna().all()
    tabela = app.dataframe[1].value
    ponto = tabela.query("Grupo == 1 and Tempo_h == 24 and Analito == 'Etanol'").iloc[0]
    assert ponto["Media"] == pytest.approx(4.756833333333333)
    assert ponto["Desvio padrao"] == pytest.approx(stdev([4.9419, 4.6412, 4.6874]))
    for carboidrato in ["DP4+", "DP3", "DP2", "Glicose", "Frutose"]:
        app.selectbox[0].select(carboidrato).run()
        assert figuras(app)[2]["layout"]["yaxis"]["range"] == charts[2]["layout"]["yaxis"]["range"]
    app.selectbox(key="metrica_comparacao_temporal").select("Glicose").run()
    assert figuras(app)[4]["layout"]["yaxis"]["range"] == figuras(app)[2]["layout"]["yaxis"]["range"]
    app.sidebar.radio[0].set_value("Replicas individuais").run()
    charts = figuras(app)
    assert len(charts[0]["data"]) == 12
    for serie in charts[0]["data"]:
        assert array_plotly(serie["x"])[0] == array_plotly(serie["y"])[0] == 0
    app.sidebar.multiselect[1].set_value([24, 48]).run()
    for serie in figuras(app)[0]["data"]:
        assert array_plotly(serie["x"]).tolist() == [24, 48]
    app.sidebar.toggle[0].set_value(False).run()
    assert figuras(app)[2]["layout"]["yaxis"]["range"][0] <= 0
    app.sidebar.multiselect[1].set_value([0]).run()
    assert not app.exception
    app.sidebar.multiselect[0].set_value([]).run()
    assert not app.exception
    assert len(app.warning) == 1
