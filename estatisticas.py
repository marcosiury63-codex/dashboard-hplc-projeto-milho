"""Estatisticas das leituras HPLC, sem alterar a planilha experimental."""

import numpy as np
import pandas as pd

ACUCARES = ["DP4+", "DP3", "DP2", "Glicose", "Frutose"]
ANALITOS = ACUCARES + [
    "Acido_latico", "Glicerol", "Acido_acetico", "Etanol", "Acucares_totais",
]


def resumir_leituras(dados: pd.DataFrame, incluir_zero_etanol: bool) -> pd.DataFrame:
    """Media, DP amostral (ddof=1), n valido e DP relativo por grupo/tempo.

    Usa as leituras disponiveis: triplicatas nos tempos experimentais e duas
    leituras em 0 h na planilha original. Ausentes nao entram no denominador.
    O zero de etanol e uma convencao de visualizacao, com n=0.
    """
    grupos = dados.groupby(["Grupo", "Tempo_h"])[ANALITOS]
    resumo = pd.concat(
        [grupos.mean(), grupos.std(ddof=1).add_suffix("_dp"),
         grupos.count().add_suffix("_n")],
        axis=1,
    ).reset_index()

    if incluir_zero_etanol:
        sem_zero = sorted(set(dados["Grupo"]) - set(
            resumo.loc[resumo["Tempo_h"].eq(0), "Grupo"]
        ))
        if sem_zero:
            zeros = pd.DataFrame({"Grupo": sem_zero, "Tempo_h": 0})
            resumo = pd.concat([resumo, zeros], ignore_index=True)

    for analito in ANALITOS:
        resumo[f"{analito}_n"] = resumo[f"{analito}_n"].fillna(0).astype(int)
        # Uma unica leitura nao permite estimar dispersao; media zero nao
        # permite calcular um erro relativo. Ambos permanecem ausentes.
        resumo[f"{analito}_erro_relativo"] = (
            100 * resumo[f"{analito}_dp"] / resumo[analito].abs().replace(0, np.nan)
        )

    zero_assumido = (
        resumo["Tempo_h"].eq(0) & resumo["Etanol_n"].eq(0)
        & incluir_zero_etanol
    )
    resumo.loc[zero_assumido, ["Etanol", "Etanol_dp", "Etanol_erro_relativo"]] = 0.0
    resumo["Etanol_origem"] = np.where(
        zero_assumido, "Zero assumido (sem medicao experimental)", "Leituras HPLC"
    )
    return resumo.sort_values(["Grupo", "Tempo_h"]).reset_index(drop=True)


def preparar_replicas(dados: pd.DataFrame, resumo: pd.DataFrame,
                     incluir_zero_etanol: bool) -> pd.DataFrame:
    """Mantem curvas individuais e associa a dispersao do tratamento/tempo."""
    chaves = ["Grupo", "Replica", "Tempo_h"]
    # Em 0 h ha duas injecoes com o mesmo identificador de replica.
    base = dados.groupby(chaves, as_index=False)[ANALITOS].mean()
    if incluir_zero_etanol:
        grupos_zero_assumido = resumo.loc[
            resumo["Tempo_h"].eq(0) & resumo["Etanol_n"].eq(0), "Grupo"
        ]
        series = dados.loc[dados["Grupo"].isin(grupos_zero_assumido), ["Grupo", "Replica"]].drop_duplicates()
        existentes = base.loc[base["Tempo_h"].eq(0), ["Grupo", "Replica"]]
        faltantes = series.merge(existentes, how="left", indicator=True)
        faltantes = faltantes.loc[faltantes["_merge"].eq("left_only"), ["Grupo", "Replica"]]
        if not faltantes.empty:
            base = pd.concat([base, faltantes.assign(Tempo_h=0)], ignore_index=True)
        zero_assumido = (
            base["Tempo_h"].eq(0) & base["Etanol"].isna()
            & base["Grupo"].isin(grupos_zero_assumido)
        )
        base.loc[zero_assumido, "Etanol"] = 0.0

    colunas_estatisticas = [c for c in resumo if c not in ANALITOS]
    base = base.merge(resumo[colunas_estatisticas], on=["Grupo", "Tempo_h"], how="left")
    return base.sort_values(chaves).reset_index(drop=True)


def valores_com_erro(base: pd.DataFrame, analito: str) -> pd.Series:
    """Limites dos pontos e barras em unidades do eixo Y."""
    erro = base[f"{analito}_dp"].fillna(0)
    return pd.concat([base[analito] - erro, base[analito] + erro], ignore_index=True)


def faixa_acucares(base: pd.DataFrame, margem: float = 0.08) -> list[float]:
    """Escala comum baseada no DP4+, com origem zero e barras visiveis.

    Expande a mesma faixa de todos os acucares se, em um recorte dos filtros,
    outro carboidrato ou sua barra exceder a faixa de referencia do DP4+.
    """
    limites = pd.concat([valores_com_erro(base, a) for a in ACUCARES]).dropna()
    minimo = min(0.0, float(limites.min())) if not limites.empty else 0.0
    maximo = max(0.0, float(limites.max())) if not limites.empty else 0.0
    folga = (maximo - minimo) * margem if maximo > minimo else 0.1
    return [minimo - folga if minimo < 0 else 0.0, maximo + folga]
