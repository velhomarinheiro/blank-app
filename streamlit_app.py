"""Painel Brasil: indicadores econômicos, sociais e fiscais (1995–2026) e comparativo internacional.

Rode com:  streamlit run streamlit_app.py
"""

import streamlit as st

from painel import dados as d
from painel import visual as v
from painel.secoes import contas_publicas, fontes, mundo, poder_de_compra, seguranca, social, tributacao, visao_geral

st.set_page_config(
    page_title="Brasil em dados",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)
v.aplica_css()

st.markdown('<div class="titulo-painel">Brasil em dados, 1995–2026</div>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitulo">Economia, condições de vida, poder de compra, impostos, contas públicas e segurança do Brasil, '
    "com comparações internacionais. Dados abertos de IBGE, Ipea, DIEESE, Tesouro, Banco Central, "
    "Fórum Brasileiro de Segurança Pública, OCDE, FMI e Banco Mundial.</p>",
    unsafe_allow_html=True,
)

# Filtros numa linha, acima de todos os gráficos.
col1, col2 = st.columns([1, 1], gap="large")
with col1:
    inicio, fim = st.slider("Período", min_value=1990, max_value=2026, value=(1995, 2026), key="periodo")
with col2:
    tipos = st.pills(
        "Tipo de dado",
        options=list(d.TIPOS),
        default=list(d.TIPOS),
        selection_mode="multi",
        format_func=d.TIPOS.get,
        key="tipos",
        help="Oficial e série histórica vêm das fontes; cálculos são contas próprias; estimativas vêm de imprensa "
             "ou terceiros.",
    )
v.legenda_tipos()

ABAS = [
    ("Visão geral", visao_geral),
    ("Social", social),
    ("Poder de compra", poder_de_compra),
    ("Tributação", tributacao),
    ("Contas públicas", contas_publicas),
    ("Segurança", seguranca),
    ("Mundo", mundo),
    ("Fontes e método", fontes),
]
for aba, (_, secao) in zip(st.tabs([nome for nome, _ in ABAS]), ABAS):
    with aba:
        secao.mostra(inicio, fim, tipos or list(d.TIPOS))
