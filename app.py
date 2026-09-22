import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Dashboard HPLC - Projeto Milho",
    page_icon="⚙️",
    layout="wide",
)

# -----------------------------
# Configuracoes visuais
# -----------------------------
BG = "#0b0b0f"
BG_GRADIENT_1 = "#121217"
BG_GRADIENT_2 = "#0b0b0f"
CARD = "#17171d"
CARD_ALT = "#1c1c24"
TEXT = "#f5f5f7"
MUTED = "#b7b9c2"
GRID = "rgba(255,255,255,0.10)"
BORDER = "rgba(255,255,255,0.08)"
ACCENT = "#ff6a00"
ACCENT_2 = "#ff8c42"
ACCENT_3 = "#ffb36b"
ACCENT_RED = "#ff4d4f"
COLORWAY = ["#FF6B00", "#00D1FF", "#FF3D81", "#FFD166", "#8AFF80", "#B388FF"]

# Cores fixas por tratamento. Assim, a mesma curva conserva a mesma cor
# mesmo quando outros tratamentos sao removidos pelos filtros.
CORES_TRATAMENTOS = {
    "30% FT-858 + CAT-1": "#FF6B00",  # laranja intenso
    "30% TMSC": "#00D1FF",            # azul-ciano
    "42% FT-858 + CAT-1": "#FF3D81",  # magenta/vermelho
    "42% TMSC": "#FFD166",            # amarelo-dourado
}

# Nomes dos tratamentos definidos para os quatro grupos.
NOMES_GRUPOS = {
    1: "30% FT-858 + CAT-1",
    2: "30% TMSC",
    3: "42% FT-858 + CAT-1",
    4: "42% TMSC",
}

st.markdown(
    f"""
    <style>
        .stApp {{
            background:
                radial-gradient(circle at top right, rgba(255,106,0,0.18), transparent 28%),
                radial-gradient(circle at top left, rgba(255,77,79,0.12), transparent 22%),
                linear-gradient(180deg, {BG_GRADIENT_1} 0%, {BG_GRADIENT_2} 100%);
            color: {TEXT};
        }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #121219 0%, #0d0d12 100%);
            border-right: 1px solid {BORDER};
        }}
        [data-testid="stSidebar"] * {{ color: {TEXT}; }}
        [data-testid="stMetric"] {{
            background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
            border: 1px solid {BORDER};
            border-radius: 18px;
            padding: 14px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.22);
        }}
        [data-testid="stMetricLabel"] {{ color: {MUTED}; }}
        [data-testid="stMetricValue"] {{ color: {TEXT}; }}
        .block-container {{ padding-top: 1.3rem; }}
        h1, h2, h3, p, label, .stMarkdown {{ color: {TEXT}; }}
        .small-note {{ color: {MUTED}; font-size: 0.92rem; line-height: 1.45; }}
        .hero-card {{
            border: 1px solid {BORDER};
            background: linear-gradient(135deg, rgba(255,106,0,0.11), rgba(255,77,79,0.05) 35%, rgba(255,255,255,0.02) 100%);
            border-radius: 24px;
            padding: 20px 24px;
            margin-bottom: 16px;
            box-shadow: 0 18px 40px rgba(0,0,0,0.24);
        }}
        .hero-badge {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            font-size: 0.85rem;
            background: rgba(255,106,0,0.15);
            border: 1px solid rgba(255,106,0,0.35);
            color: {ACCENT_3};
            margin-bottom: 10px;
        }}
        .section-chip {{
            display: inline-block;
            padding: 5px 11px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            background: rgba(255,255,255,0.04);
            color: {ACCENT_3};
            border: 1px solid rgba(255,255,255,0.08);
            letter-spacing: 0.02em;
            text-transform: uppercase;
        }}
        .stButton>button, .stDownloadButton>button {{
            background: linear-gradient(135deg, {ACCENT} 0%, {ACCENT_RED} 100%);
            color: white;
            border: 0;
            border-radius: 12px;
            font-weight: 600;
            box-shadow: 0 10px 22px rgba(255,106,0,0.22);
        }}
        .stButton>button:hover, .stDownloadButton>button:hover {{
            filter: brightness(1.05);
        }}
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div {{
            background-color: {CARD} !important;
            border-color: {BORDER} !important;
        }}
        div[data-testid="stDataFrame"] {{
            border: 1px solid {BORDER};
            border-radius: 16px;
            overflow: hidden;
        }}
        .sidebar-logo-wrap {{
            text-align: center;
            padding-top: 0.2rem;
            padding-bottom: 0.4rem;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Funcoes auxiliares
# -----------------------------
def adicionar_zero_h_compartilhado(
    df: pd.DataFrame,
    grupo_origem: int,
    grupo_destino: int,
) -> pd.DataFrame:
    """
    Replica os registros de 0 h de um grupo para outro quando o grupo destino
    nao possui 0 h. Isso segue a equivalencia experimental definida para o projeto:
      - Grupo 1 -> Grupo 2
      - Grupo 3 -> Grupo 4

    Os registros gerados ficam identificados na coluna Origem_dado para nao serem
    confundidos com leituras independentes do HPLC.
    """
    tem_destino = ((df["Grupo"] == grupo_destino) & (df["Tempo_h"] == 0)).any()
    if tem_destino:
        return df

    origem = df[(df["Grupo"] == grupo_origem) & (df["Tempo_h"] == 0)].copy()
    if origem.empty:
        return df

    origem["Grupo"] = grupo_destino
    origem["Descricao"] = origem["Descricao"].astype(str).str.replace(
        rf"^{grupo_origem}\.",
        f"{grupo_destino}.",
        regex=True,
    )
    origem["Origem_dado"] = f"0 h compartilhada com o grupo {grupo_origem}"

    return pd.concat([df, origem], ignore_index=True)


def faixa_y_ajustada(valores: pd.Series, margem: float = 0.08):
    """Calcula uma faixa de eixo Y mais fechada para destacar variacoes nas curvas."""
    serie = pd.to_numeric(valores, errors="coerce").dropna()
    if serie.empty:
        return None

    minimo = float(serie.min())
    maximo = float(serie.max())

    if np.isclose(minimo, maximo):
        referencia = max(abs(maximo), 1.0)
        folga = referencia * 0.10
    else:
        folga = (maximo - minimo) * margem

    limite_inferior = minimo - folga
    limite_superior = maximo + folga

    if minimo >= 0 and limite_inferior < 0:
        limite_inferior = 0

    return [limite_inferior, limite_superior]


def tema_figura(fig, titulo_y=None, valores_y=None, escala_ajustada=False, is_bar=False):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.01)",
        font=dict(color=TEXT),
        colorway=COLORWAY,
        legend_title_text="",
        margin=dict(l=20, r=20, t=70, b=25),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=11),
            bgcolor="rgba(0,0,0,0)"
        ),
        title=dict(font=dict(size=20)),
    )
    fig.update_xaxes(
        gridcolor=GRID,
        zerolinecolor=GRID,
        showline=True,
        linecolor="rgba(255,255,255,0.12)",
    )
    fig.update_yaxes(
        gridcolor=GRID,
        zerolinecolor=GRID,
        title=titulo_y,
        nticks=8,
        showline=True,
        linecolor="rgba(255,255,255,0.12)",
    )

    if not is_bar:
        fig.update_traces(
            line=dict(width=3.6),
            marker=dict(size=9, line=dict(width=1.4, color="#0b0b0f")),
            opacity=0.98,
        )

    if escala_ajustada and valores_y is not None:
        faixa = faixa_y_ajustada(valores_y)
        if faixa is not None:
            fig.update_yaxes(range=faixa)

    return fig


# -----------------------------
# Leitura e tratamento dos dados
# -----------------------------
@st.cache_data
def carregar_dados(caminho_excel) -> pd.DataFrame:
    df = pd.read_excel(caminho_excel, sheet_name=" HPLC", header=1, usecols="A:J")
    df.columns = [
        "Descricao",
        "DP4+",
        "DP3",
        "DP2",
        "Glicose",
        "Frutose",
        "Acido_latico",
        "Glicerol",
        "Acido_acetico",
        "Etanol",
    ]

    df = df[df["Descricao"].notna()].copy()
    df = df[~df["Descricao"].astype(str).str.contains("%\\(", regex=True, na=False)].copy()

    padrao = re.compile(r"^(?P<grupo>\d+)\.(?P<replica>\d+)\s+(?P<tempo>\d+)h$")
    extraidos = df["Descricao"].astype(str).str.extract(padrao)
    df["Grupo"] = pd.to_numeric(extraidos["grupo"], errors="coerce").astype("Int64")
    df["Replica"] = pd.to_numeric(extraidos["replica"], errors="coerce").astype("Int64")
    df["Tempo_h"] = pd.to_numeric(extraidos["tempo"], errors="coerce").astype("Int64")
    df = df[df["Grupo"].notna() & df["Tempo_h"].notna()].copy()

    df["Origem_dado"] = "Leitura original"

    analitos = [
        "DP4+", "DP3", "DP2", "Glicose", "Frutose",
        "Acido_latico", "Glicerol", "Acido_acetico", "Etanol",
    ]
    for col in analitos:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = adicionar_zero_h_compartilhado(df, grupo_origem=1, grupo_destino=2)
    df = adicionar_zero_h_compartilhado(df, grupo_origem=3, grupo_destino=4)

    df["Tratamento"] = df["Grupo"].astype(int).map(NOMES_GRUPOS)

    acucares = ["DP4+", "DP3", "DP2", "Glicose", "Frutose"]
    df["Acucares_totais"] = df[acucares].sum(axis=1, min_count=1)

    return df


ARQUIVO_PADRAO = Path(__file__).with_name("Projeto Milho - Marcos.xlsx")
LOGO_PATH = Path(__file__).with_name("logo_dashboard_industrial.png")

# -----------------------------
# Sidebar
# -----------------------------
if LOGO_PATH.exists():
    st.sidebar.markdown("<div class='sidebar-logo-wrap'>", unsafe_allow_html=True)
    st.sidebar.image(str(LOGO_PATH), width=120)
    st.sidebar.markdown("</div>", unsafe_allow_html=True)

st.sidebar.markdown("### Painel de controle")
st.sidebar.caption("Filtros, visualizacao e exportacao")

arquivo_upload = st.sidebar.file_uploader("Carregar outro arquivo Excel", type=["xlsx"])
fonte = arquivo_upload if arquivo_upload is not None else str(ARQUIVO_PADRAO)

df = carregar_dados(fonte)

# -----------------------------
# Header principal
# -----------------------------
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=150)
with header_col2:
    st.markdown(
        """
        <div class='hero-card'>
            <div class='hero-badge'>Dashboard industrial | HPLC</div>
            <h1 style='margin:0;'>Dashboard Interativo - Analises Cromatograficas</h1>
            <div style='height:8px'></div>
            <p style='margin:0; color:#d7dae0; font-size:1.03rem;'>Projeto Milho | acompanhamento da fermentacao por tratamento, replica e tempo com visual mais tecnico, moderno e orientado a comparacoes de processo.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------
# Filtros
# -----------------------------
st.sidebar.header("Filtros")

grupos_disponiveis = sorted(df["Grupo"].dropna().astype(int).unique().tolist())
grupos = st.sidebar.multiselect(
    "Tratamentos",
    options=grupos_disponiveis,
    default=grupos_disponiveis,
    format_func=lambda g: NOMES_GRUPOS.get(g, f"Grupo {g}"),
)

tempos_disponiveis = sorted(df["Tempo_h"].dropna().astype(int).unique().tolist())
tempos = st.sidebar.multiselect(
    "Tempos (h)",
    options=tempos_disponiveis,
    default=tempos_disponiveis,
)

modo = st.sidebar.radio(
    "Como exibir os dados?",
    ["Media por tratamento", "Replicas individuais"],
    index=0,
)

escala_ajustada = st.sidebar.toggle(
    "Escala Y mais detalhada",
    value=True,
    help=(
        "Fecha automaticamente a faixa do eixo Y dos graficos de linha para destacar "
        "melhor as curvas de crescimento e queda. O grafico de barras continua partindo de zero."
    ),
)

filtrado = df[
    df["Grupo"].astype(int).isin(grupos)
    & df["Tempo_h"].astype(int).isin(tempos)
].copy()

if filtrado.empty:
    st.warning("Nenhum dado corresponde aos filtros selecionados.")
    st.stop()

# -----------------------------
# KPIs
# -----------------------------
ultimo_tempo = int(filtrado["Tempo_h"].max())
final = filtrado[filtrado["Tempo_h"] == ultimo_tempo]

etanol_final = final["Etanol"].mean()
glicose_final = final["Glicose"].mean()
acucares_final = final["Acucares_totais"].mean()
numero_amostras = len(filtrado)

st.markdown("<div class='section-chip'>Visao geral</div>", unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Registros filtrados", f"{numero_amostras}")
c2.metric(
    f"Etanol medio em {ultimo_tempo} h",
    "-" if pd.isna(etanol_final) else f"{etanol_final:.2f} % v/v",
)
c3.metric(
    f"Glicose media em {ultimo_tempo} h",
    "-" if pd.isna(glicose_final) else f"{glicose_final:.2f} g/100 mL",
)
c4.metric(
    f"Acucares totais em {ultimo_tempo} h",
    "-" if pd.isna(acucares_final) else f"{acucares_final:.2f} g/100 mL",
)

st.markdown(
    "<div class='small-note'>"
    "Observacao: no arquivo original, <b>n.a.</b> indica nao detectado e e tratado como ausente, nao como zero. "
    "Para 0 h, os dados do tratamento 30% TMSC sao compartilhados com 30% FT-858 + CAT-1, e os de 42% TMSC "
    "sao compartilhados com 42% FT-858 + CAT-1, conforme a equivalencia experimental informada."
    "</div>",
    unsafe_allow_html=True,
)

# -----------------------------
# Preparacao para graficos
# -----------------------------
if modo == "Media por tratamento":
    numericas = [
        "DP4+", "DP3", "DP2", "Glicose", "Frutose",
        "Acido_latico", "Glicerol", "Acido_acetico", "Etanol", "Acucares_totais",
    ]
    base = filtrado.groupby(["Grupo", "Tempo_h"], as_index=False)[numericas].mean()
    base["Serie"] = base["Grupo"].astype(int).map(NOMES_GRUPOS)
else:
    base = filtrado.copy()
    base["Serie"] = base["Tratamento"] + " | rep. " + base["Replica"].astype(str)

# Mapa de cores dinamico para manter identidade visual tambem nas replicas.
# Na media, usa diretamente a cor fixa do tratamento. Nas replicas, parte da
# mesma familia de cor, sem trocar a identidade do grupo.
if modo == "Media por tratamento":
    MAPA_SERIES = CORES_TRATAMENTOS.copy()
else:
    MAPA_SERIES = {}
    for _, linha in base[["Serie", "Tratamento"]].drop_duplicates().iterrows():
        MAPA_SERIES[linha["Serie"]] = CORES_TRATAMENTOS.get(linha["Tratamento"], ACCENT)

ticks_tempo = sorted(base["Tempo_h"].dropna().astype(int).unique().tolist())

# -----------------------------
# Etanol e acucares
# -----------------------------
st.markdown("<div class='section-chip'>Curvas principais</div>", unsafe_allow_html=True)
st.subheader("1. Evolucao da fermentacao")
col_esq, col_dir = st.columns(2)

with col_esq:
    fig_et = px.line(
        base,
        x="Tempo_h",
        y="Etanol",
        color="Serie",
        markers=True,
        title="Evolucao do etanol",
        labels={"Tempo_h": "Tempo (h)", "Etanol": "Etanol (% v/v)", "Serie": "Tratamento"},
        color_discrete_map=MAPA_SERIES,
        color_discrete_sequence=COLORWAY,
    )
    tema_figura(fig_et, "Etanol (% v/v)", valores_y=base["Etanol"], escala_ajustada=escala_ajustada)
    fig_et.update_xaxes(tickmode="array", tickvals=ticks_tempo)
    st.plotly_chart(fig_et, use_container_width=True)

with col_dir:
    fig_at = px.line(
        base,
        x="Tempo_h",
        y="Acucares_totais",
        color="Serie",
        markers=True,
        title="Acucares residuais totais",
        labels={"Tempo_h": "Tempo (h)", "Acucares_totais": "g/100 mL", "Serie": "Tratamento"},
        color_discrete_map=MAPA_SERIES,
        color_discrete_sequence=COLORWAY,
    )
    tema_figura(fig_at, "Acucares totais (g/100 mL)", valores_y=base["Acucares_totais"], escala_ajustada=escala_ajustada)
    fig_at.update_xaxes(tickmode="array", tickvals=ticks_tempo)
    st.plotly_chart(fig_at, use_container_width=True)

# -----------------------------
# Analitos individuais
# -----------------------------
st.markdown("<div class='section-chip'>Acucares</div>", unsafe_allow_html=True)
st.subheader("2. Composicao dos acucares")
analito_acucar = st.selectbox(
    "Selecione o carboidrato para comparar",
    ["Glicose", "DP2", "DP3", "DP4+", "Frutose"],
)
fig_ac = px.line(
    base,
    x="Tempo_h",
    y=analito_acucar,
    color="Serie",
    markers=True,
    title=f"Evolucao de {analito_acucar}",
    labels={"Tempo_h": "Tempo (h)", analito_acucar: "Concentracao (g/100 mL)", "Serie": "Tratamento"},
    color_discrete_map=MAPA_SERIES,
    color_discrete_sequence=COLORWAY,
)
tema_figura(fig_ac, "Concentracao (g/100 mL)", valores_y=base[analito_acucar], escala_ajustada=escala_ajustada)
fig_ac.update_xaxes(tickmode="array", tickvals=ticks_tempo)
st.plotly_chart(fig_ac, use_container_width=True)

# -----------------------------
# Subprodutos
# -----------------------------
st.markdown("<div class='section-chip'>Subprodutos</div>", unsafe_allow_html=True)
st.subheader("3. Subprodutos da fermentacao")
subproduto = st.selectbox(
    "Selecione o composto",
    ["Glicerol", "Acido_latico", "Acido_acetico"],
)
fig_sub = px.line(
    base,
    x="Tempo_h",
    y=subproduto,
    color="Serie",
    markers=True,
    title=f"Evolucao de {subproduto.replace('_', ' ')}",
    labels={"Tempo_h": "Tempo (h)", subproduto: "Concentracao (g/100 mL)", "Serie": "Tratamento"},
    color_discrete_map=MAPA_SERIES,
    color_discrete_sequence=COLORWAY,
)
tema_figura(fig_sub, "Concentracao (g/100 mL)", valores_y=base[subproduto], escala_ajustada=escala_ajustada)
fig_sub.update_xaxes(tickmode="array", tickvals=ticks_tempo)
st.plotly_chart(fig_sub, use_container_width=True)

# -----------------------------
# Comparacao temporal entre tratamentos
# -----------------------------
st.markdown("<div class='section-chip'>Comparacao</div>", unsafe_allow_html=True)
st.subheader("4. Comparacao temporal entre tratamentos")

metricas_comparacao = {
    "Etanol": ("Etanol", "Etanol (% v/v)"),
    "Glicose": ("Glicose", "Glicose (g/100 mL)"),
    "Acucares totais": ("Acucares_totais", "Acucares totais (g/100 mL)"),
    "Glicerol": ("Glicerol", "Glicerol (g/100 mL)"),
}

col_metrica, col_tempo = st.columns([1.25, 2])
with col_metrica:
    metrica_escolhida = st.selectbox(
        "Variavel para comparacao",
        options=list(metricas_comparacao.keys()),
        index=0,
        key="metrica_comparacao_temporal",
    )

with col_tempo:
    tempo_comparacao = st.select_slider(
        "Destacar tempo (h)",
        options=sorted(filtrado["Tempo_h"].astype(int).unique()),
        value=ultimo_tempo,
        key="tempo_comparacao_temporal",
    )

coluna_metrica, titulo_y_comparacao = metricas_comparacao[metrica_escolhida]

comp_temporal = (
    filtrado
    .groupby(["Grupo", "Tempo_h"], as_index=False)[coluna_metrica]
    .mean()
)
comp_temporal["Tratamento"] = comp_temporal["Grupo"].astype(int).map(NOMES_GRUPOS)

fig_comp = px.line(
    comp_temporal,
    x="Tempo_h",
    y=coluna_metrica,
    color="Tratamento",
    markers=True,
    title=f"{metrica_escolhida}: comparacao da evolucao entre tratamentos",
    labels={
        "Tempo_h": "Tempo de fermentacao (h)",
        coluna_metrica: titulo_y_comparacao,
        "Tratamento": "Tratamento",
    },
    color_discrete_map=CORES_TRATAMENTOS,
    color_discrete_sequence=COLORWAY,
)

tema_figura(
    fig_comp,
    titulo_y_comparacao,
    valores_y=comp_temporal[coluna_metrica],
    escala_ajustada=escala_ajustada,
)
fig_comp.update_xaxes(
    tickmode="array",
    tickvals=sorted(comp_temporal["Tempo_h"].dropna().astype(int).unique().tolist()),
)

# Linha vertical para manter a leitura de um tempo de referencia sem perder a curva completa.
fig_comp.add_vline(
    x=int(tempo_comparacao),
    line_width=1.5,
    line_dash="dash",
    line_color="rgba(255,255,255,0.65)",
)
fig_comp.add_annotation(
    x=int(tempo_comparacao),
    y=1.03,
    yref="paper",
    text=f"Referencia: {tempo_comparacao} h",
    showarrow=False,
    font=dict(color=TEXT, size=11),
    bgcolor="rgba(20,20,24,0.85)",
    bordercolor="rgba(255,255,255,0.12)",
    borderwidth=1,
    borderpad=5,
)

st.plotly_chart(fig_comp, use_container_width=True)

st.markdown(
    "<div class='small-note'>"
    "Nesta comparacao, cada linha representa um tratamento ao longo do tempo. "
    "A linha tracejada indica apenas o tempo selecionado como referencia visual."
    "</div>",
    unsafe_allow_html=True,
)

# -----------------------------
# Tabela
# -----------------------------
st.markdown("<div class='section-chip'>Base filtrada</div>", unsafe_allow_html=True)
st.subheader("5. Dados detalhados")
colunas_tabela = [
    "Descricao", "Tratamento", "Grupo", "Replica", "Tempo_h", "Origem_dado",
    "DP4+", "DP3", "DP2", "Glicose", "Frutose",
    "Acido_latico", "Glicerol", "Acido_acetico", "Etanol", "Acucares_totais",
]
st.dataframe(
    filtrado[colunas_tabela].sort_values(["Grupo", "Tempo_h", "Replica"]),
    use_container_width=True,
    hide_index=True,
)

csv = filtrado[colunas_tabela].to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "Baixar dados filtrados em CSV",
    data=csv,
    file_name="hplc_dados_filtrados.csv",
    mime="text/csv",
)

with st.expander("Observacoes sobre a base de dados"):
    st.write(
        "Os registros originais de 0 h existem para os grupos 1 e 3. Para representar corretamente "
        "o desenho experimental no dashboard, os valores de 1.1 0 h sao usados tambem para 2.1 0 h, "
        "e os valores de 3.1 0 h sao usados tambem para 4.1 0 h. Esses pontos ficam identificados como "
        "dados compartilhados na tabela detalhada; o arquivo Excel original nao e alterado pelo dashboard."
    )
    st.write(
        "A opcao 'Escala Y mais detalhada' ajusta apenas os graficos de linha. O grafico de barras "
        "continua com origem em zero para preservar uma comparacao visual adequada entre tratamentos."
    )
