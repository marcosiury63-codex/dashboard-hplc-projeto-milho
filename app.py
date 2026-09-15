import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Dashboard HPLC - Projeto Milho",
    page_icon="🌽",
    layout="wide",
)

# -----------------------------
# Configuracoes visuais
# -----------------------------
BG = "#0f2029"
CARD = "#162d38"
TEXT = "#f5f7f8"
MUTED = "#a9bcc5"
GRID = "rgba(255,255,255,0.10)"

st.markdown(
    f"""
    <style>
        .stApp {{ background-color: {BG}; color: {TEXT}; }}
        [data-testid="stSidebar"] {{ background-color: #102630; }}
        [data-testid="stMetric"] {{
            background: {CARD};
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px;
            padding: 14px;
        }}
        h1, h2, h3, p, label, .stMarkdown {{ color: {TEXT}; }}
        .small-note {{ color: {MUTED}; font-size: 0.9rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Leitura e tratamento dos dados
# -----------------------------
@st.cache_data
def carregar_dados(caminho_excel: str) -> pd.DataFrame:
    # A planilha possui titulo na linha 1 e cabecalhos reais na linha 2.
    df = pd.read_excel(caminho_excel, sheet_name=" HPLC", header=1, usecols="A:J")

    # Renomeia as colunas para nomes simples e consistentes.
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

    # Remove a linha de unidades e qualquer linha vazia.
    df = df[df["Descricao"].notna()].copy()
    df = df[~df["Descricao"].astype(str).str.contains("%\\(", regex=True, na=False)].copy()

    # Extrai grupo, replica e tempo de textos como '3.2 72h'.
    padrao = re.compile(r"^(?P<grupo>\d+)\.(?P<replica>\d+)\s+(?P<tempo>\d+)h$")
    extraidos = df["Descricao"].astype(str).str.extract(padrao)
    df["Grupo"] = pd.to_numeric(extraidos["grupo"], errors="coerce").astype("Int64")
    df["Replica"] = pd.to_numeric(extraidos["replica"], errors="coerce").astype("Int64")
    df["Tempo_h"] = pd.to_numeric(extraidos["tempo"], errors="coerce").astype("Int64")
    df = df[df["Grupo"].notna() & df["Tempo_h"].notna()].copy()

    # 'n.a.' significa nao detectado no arquivo original.
    # Aqui tratamos como valor ausente (NaN), e NAO como zero.
    analitos = [
        "DP4+", "DP3", "DP2", "Glicose", "Frutose",
        "Acido_latico", "Glicerol", "Acido_acetico", "Etanol",
    ]
    for col in analitos:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Acucares totais em g/100 mL. Nao mistura com etanol, que esta em % v/v.
    acucares = ["DP4+", "DP3", "DP2", "Glicose", "Frutose"]
    df["Acucares_totais"] = df[acucares].sum(axis=1, min_count=1)

    return df


def tema_figura(fig, titulo_y=None):
    fig.update_layout(
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(color=TEXT),
        legend_title_text="",
        margin=dict(l=20, r=20, t=55, b=25),
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, title=titulo_y)
    return fig


ARQUIVO_PADRAO = Path(__file__).with_name("Projeto Milho - Marcos.xlsx")

st.title("🌽 Dashboard Interativo - Analises Cromatograficas (HPLC)")
st.caption("Projeto Milho | acompanhamento da fermentacao por grupo, replica e tempo")

# Permite usar o arquivo que acompanha o projeto ou carregar outro arquivo depois.
arquivo_upload = st.sidebar.file_uploader("Carregar outro arquivo Excel", type=["xlsx"])
fonte = arquivo_upload if arquivo_upload is not None else str(ARQUIVO_PADRAO)

df = carregar_dados(fonte)

# -----------------------------
# Filtros
# -----------------------------
st.sidebar.header("Filtros")

grupos_disponiveis = sorted(df["Grupo"].dropna().astype(int).unique().tolist())
grupos = st.sidebar.multiselect(
    "Grupos",
    options=grupos_disponiveis,
    default=grupos_disponiveis,
)

tempos_disponiveis = sorted(df["Tempo_h"].dropna().astype(int).unique().tolist())
tempos = st.sidebar.multiselect(
    "Tempos (h)",
    options=tempos_disponiveis,
    default=tempos_disponiveis,
)

modo = st.sidebar.radio(
    "Como exibir os dados?",
    ["Media por grupo", "Replicas individuais"],
    index=0,
)

filtrado = df[df["Grupo"].astype(int).isin(grupos) & df["Tempo_h"].astype(int).isin(tempos)].copy()

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

c1, c2, c3, c4 = st.columns(4)
c1.metric("Registros filtrados", f"{numero_amostras}")
c2.metric(f"Etanol medio em {ultimo_tempo} h", "-" if pd.isna(etanol_final) else f"{etanol_final:.2f} % v/v")
c3.metric(f"Glicose media em {ultimo_tempo} h", "-" if pd.isna(glicose_final) else f"{glicose_final:.2f} g/100 mL")
c4.metric(f"Acucares totais em {ultimo_tempo} h", "-" if pd.isna(acucares_final) else f"{acucares_final:.2f} g/100 mL")

st.markdown("<div class='small-note'>Observacao: no arquivo original, <b>n.a.</b> indica nao detectado. No dashboard esses casos sao tratados como ausentes, e nao como zero.</div>", unsafe_allow_html=True)

# -----------------------------
# Preparacao para graficos
# -----------------------------
if modo == "Media por grupo":
    numericas = [
        "DP4+", "DP3", "DP2", "Glicose", "Frutose",
        "Acido_latico", "Glicerol", "Acido_acetico", "Etanol", "Acucares_totais",
    ]
    base = filtrado.groupby(["Grupo", "Tempo_h"], as_index=False)[numericas].mean()
    base["Serie"] = "Grupo " + base["Grupo"].astype(str)
else:
    base = filtrado.copy()
    base["Serie"] = "G" + base["Grupo"].astype(str) + "." + base["Replica"].astype(str)

# -----------------------------
# Etanol e acucares
# -----------------------------
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
        labels={"Tempo_h": "Tempo (h)", "Etanol": "Etanol (% v/v)", "Serie": "Serie"},
    )
    tema_figura(fig_et, "Etanol (% v/v)")
    st.plotly_chart(fig_et, use_container_width=True)

with col_dir:
    fig_at = px.line(
        base,
        x="Tempo_h",
        y="Acucares_totais",
        color="Serie",
        markers=True,
        title="Acucares residuais totais",
        labels={"Tempo_h": "Tempo (h)", "Acucares_totais": "g/100 mL", "Serie": "Serie"},
    )
    tema_figura(fig_at, "Acucares totais (g/100 mL)")
    st.plotly_chart(fig_at, use_container_width=True)

# -----------------------------
# Analitos individuais
# -----------------------------
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
    labels={"Tempo_h": "Tempo (h)", analito_acucar: "Concentracao (g/100 mL)", "Serie": "Serie"},
)
tema_figura(fig_ac, "Concentracao (g/100 mL)")
st.plotly_chart(fig_ac, use_container_width=True)

# -----------------------------
# Subprodutos
# -----------------------------
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
    labels={"Tempo_h": "Tempo (h)", subproduto: "Concentracao (g/100 mL)", "Serie": "Serie"},
)
tema_figura(fig_sub, "Concentracao (g/100 mL)")
st.plotly_chart(fig_sub, use_container_width=True)

# -----------------------------
# Comparacao no tempo selecionado
# -----------------------------
st.subheader("4. Comparacao entre grupos")
tempo_comparacao = st.select_slider(
    "Tempo para comparacao",
    options=sorted(filtrado["Tempo_h"].astype(int).unique()),
    value=ultimo_tempo,
)

comp = filtrado[filtrado["Tempo_h"].astype(int) == int(tempo_comparacao)]
comp_media = comp.groupby("Grupo", as_index=False)[["Etanol", "Glicose", "Acucares_totais", "Glicerol"]].mean()
comp_media["Grupo_nome"] = "Grupo " + comp_media["Grupo"].astype(str)

fig_bar = px.bar(
    comp_media,
    x="Grupo_nome",
    y="Etanol",
    text_auto=".2f",
    title=f"Etanol medio por grupo em {tempo_comparacao} h",
    labels={"Grupo_nome": "Grupo", "Etanol": "Etanol (% v/v)"},
)
tema_figura(fig_bar, "Etanol (% v/v)")
st.plotly_chart(fig_bar, use_container_width=True)

# -----------------------------
# Tabela
# -----------------------------
st.subheader("5. Dados detalhados")
colunas_tabela = [
    "Descricao", "Grupo", "Replica", "Tempo_h",
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

# -----------------------------
# Nota sobre a base
# -----------------------------
with st.expander("Observacoes sobre a base de dados"):
    st.write(
        "Os tempos de 0 h nao possuem o mesmo numero de registros dos demais tempos na planilha original. "
        "Por isso, o dashboard nao cria valores ausentes nem replica dados entre grupos. As comparacoes exibem somente os registros realmente presentes no arquivo."
    )
