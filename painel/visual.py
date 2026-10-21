"""Aparência do painel: cores, CSS, cartões de indicadores e ajustes comuns dos gráficos.

Estilo inspirado em https://gab-berger.github.io/idh-brasil/: fundo limpo, fonte do sistema,
títulos discretos, paleta Okabe-Ito (segura para daltonismo) e o Brasil sempre em laranja.
"""

from __future__ import annotations

import html
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Paletas categóricas validadas (ordem fixa; o Brasil é sempre o primeiro slot).
# Claro: Okabe-Ito. Escuro: os mesmos matizes com luminosidade ajustada ao fundo escuro.
PALETAS = {
    "light": {
        "brasil": "#d55e00",
        "serie": ["#0072b2", "#009e73", "#e69f00", "#cc79a7", "#6250d6"],
        "neutro": "#8a8f98",
        "neutro_claro": "#c9ccd1",
        "positivo": "#0072b2",
        "negativo": "#d55e00",
        "faixa": "rgba(127,127,127,0.07)",
        "fundo": "#ffffff",
    },
    "dark": {
        "brasil": "#d95926",
        "serie": ["#3987e5", "#199e70", "#c98500", "#d55181", "#9085e9"],
        "neutro": "#7d828b",
        "neutro_claro": "#4a4f57",
        "positivo": "#3987e5",
        "negativo": "#d95926",
        "faixa": "rgba(200,200,200,0.06)",
        "fundo": "#121417",
    },
}

FONTE = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"


def modo() -> str:
    try:
        tipo = st.context.theme.type
    except Exception:  # versões antigas do Streamlit
        tipo = None
    return "dark" if tipo == "dark" else "light"


def cores() -> dict:
    return PALETAS[modo()]


# ---------------------------------------------------------------- números em pt-BR


def br(numero: float | int | None, casas: int = 1, sinal: bool = False) -> str:
    """Formata no padrão brasileiro: 1.234,5."""
    if numero is None or (isinstance(numero, float) and pd.isna(numero)):
        return "—"
    texto = f"{numero:{'+' if sinal else ''},.{casas}f}"
    texto = texto.replace(",", "§").replace(".", ",").replace("§", ".")
    return texto.replace("-", "−")


# ---------------------------------------------------------------- CSS e blocos de texto

CSS = """
<style>
/* Largura de leitura confortável, como no site de referência. */
.block-container { max-width: 1080px; padding-top: 2.2rem; padding-bottom: 4rem; }
h1, h2, h3 { letter-spacing: -0.01em; }
.stMarkdown h3 { font-size: 1.1rem; margin-top: 1.6rem; }
.titulo-painel { font-size: 1.6rem; font-weight: 700; line-height: 1.2; margin: 0 0 4px; }
.subtitulo { opacity: .72; margin: 0 0 12px; max-width: 720px; }
.texto { max-width: 720px; }
.leitura { max-width: 720px; font-size: .95rem; }
.leitura b { font-weight: 600; }
.nota { font-size: .85rem; opacity: .72; max-width: 720px; margin: 4px 0 18px; }

/* Abas no topo, discretas: sublinhado azul na aba ativa. */
.stTabs [data-baseweb="tab-list"] { gap: 4px; flex-wrap: wrap; border-bottom: 1px solid rgba(127,127,127,.25); }
.stTabs [data-baseweb="tab"] { padding: 6px 10px; height: auto; min-height: 44px; }
.stTabs [data-baseweb="tab"] p { font-size: .92rem; }
.stTabs [aria-selected="true"] p { font-weight: 600; }

/* Cartões de indicadores. */
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 8px 0 16px; }
.kpi { border: 1px solid rgba(127,127,127,.25); border-radius: 10px; padding: 12px 14px;
       background: rgba(127,127,127,.05); }
.kpi .rotulo { font-size: .8rem; opacity: .72; line-height: 1.25; }
.kpi .valor { font-size: 1.55rem; font-weight: 700; font-variant-numeric: tabular-nums; line-height: 1.2; margin-top: 4px; }
.kpi .valor small { font-size: .85rem; font-weight: 600; opacity: .8; margin-left: 2px; }
.kpi .detalhe { font-size: .78rem; opacity: .72; margin-top: 4px; line-height: 1.3; }
.kpi.destaque { border-left: 4px solid var(--cor-brasil); }

/* Selos do tipo de dado. */
.selo { display: inline-block; font-size: .68rem; font-weight: 600; border-radius: 999px; padding: 1px 7px;
        margin-left: 4px; vertical-align: 1px; border: 1px solid rgba(127,127,127,.45); opacity: .85; }
.legenda-tipos { font-size: .82rem; opacity: .8; margin: 2px 0 8px; }
.legenda-tipos span { margin-right: 14px; white-space: nowrap; }

/* Frase de destaque centralizada. */
.destaque-frase { text-align: center; font-weight: 600; margin: 6px auto 12px; max-width: 720px;
                  font-variant-numeric: tabular-nums; text-wrap: balance; }
</style>
"""


def aplica_css() -> None:
    st.markdown(CSS.replace("var(--cor-brasil)", cores()["brasil"]), unsafe_allow_html=True)


def selo(tipo: str | None) -> str:
    rotulos = {"calculo": "cálculo", "estimativa": "estimativa", "serie_historica": "série histórica"}
    if tipo in rotulos:
        return f'<span class="selo">{rotulos[tipo]}</span>'
    return ""


def kpis(cartoes: list[dict]) -> None:
    """Grade de cartões. Cada cartão: rotulo, valor, unidade, detalhe, tipo, destaque."""
    partes = []
    for c in cartoes:
        classe = "kpi destaque" if c.get("destaque") else "kpi"
        unidade = f"<small>{html.escape(c['unidade'])}</small>" if c.get("unidade") else ""
        detalhe = f'<div class="detalhe">{c["detalhe"]}</div>' if c.get("detalhe") else ""
        partes.append(
            f'<div class="{classe}"><div class="rotulo">{html.escape(c["rotulo"])}{selo(c.get("tipo"))}</div>'
            f'<div class="valor">{c["valor"]}{unidade}</div>{detalhe}</div>'
        )
    st.markdown(f'<div class="kpis">{"".join(partes)}</div>', unsafe_allow_html=True)


def leitura(texto: str) -> None:
    """Parágrafo de análise curta. Aceita **negrito**."""
    texto = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", texto)
    st.markdown(f'<p class="leitura">{texto}</p>', unsafe_allow_html=True)


def nota(texto: str) -> None:
    st.markdown(f'<p class="nota">{texto}</p>', unsafe_allow_html=True)


def frase(texto: str) -> None:
    st.markdown(f'<p class="destaque-frase">{texto}</p>', unsafe_allow_html=True)


def legenda_tipos() -> None:
    st.markdown(
        '<p class="legenda-tipos">'
        "<span>● oficial / série histórica</span>"
        "<span>○ cálculo próprio (marcador vazado, barra clara)</span>"
        "<span>◇ estimativa (losango vazado, barra hachurada)</span>"
        "</p>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------- gráficos

SIMBOLOS = {"calculo": "circle-open", "estimativa": "diamond-open"}


def simbolo(tipo: str | None) -> str:
    return SIMBOLOS.get(tipo, "circle")


def padrao_barra(tipos) -> dict:
    """Barras de cálculo ficam mais claras; estimativas, hachuradas."""
    tipos = list(tipos)
    return dict(shape=["/" if t == "estimativa" else "" for t in tipos], solidity=0.35, size=6)


def opacidades(tipos) -> list[float]:
    return [0.5 if t in ("calculo", "estimativa") else 1.0 for t in tipos]


def estilo(fig: go.Figure, altura: int = 360, titulo: str | None = None, eixo_y: str | None = None,
           legenda: bool = True) -> go.Figure:
    fig.update_layout(
        height=altura,
        margin=dict(l=8, r=12, t=48 if titulo else 16, b=8),
        title=dict(text=titulo, x=0, xanchor="left", font=dict(size=15)) if titulo else None,
        separators=",.",
        font=dict(family=FONTE, size=13),
        hoverlabel=dict(font=dict(family=FONTE)),
        showlegend=legenda,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, title=None),
        bargap=0.25,
    )
    fig.update_xaxes(showgrid=False, zeroline=False, ticks="")
    fig.update_yaxes(zeroline=True, zerolinewidth=1, title=eixo_y, title_font=dict(size=12))
    return fig


def mostra(fig: go.Figure, dados: pd.DataFrame | None = None, nome: str = "dados") -> None:
    """Desenha o gráfico e, logo abaixo, a tabela com os números (e download em CSV)."""
    # Rótulos de valor fora da barra não são cortados nas bordas.
    fig.update_traces(cliponaxis=False, selector=dict(type="bar"))
    for eixo in ("xaxis", "yaxis"):
        if fig.layout[eixo].showticklabels is False:
            fig.layout[eixo].showgrid = False
    st.plotly_chart(
        fig,
        width="stretch",
        theme="streamlit",
        config={"displayModeBar": False, "scrollZoom": False},
    )
    if dados is not None:
        with st.expander("Ver dados", expanded=False):
            st.dataframe(dados, hide_index=True, width="stretch")
            st.download_button(
                "Baixar CSV",
                dados.to_csv(index=False).encode("utf-8"),
                file_name=f"{nome}.csv",
                mime="text/csv",
                key=f"baixar_{nome}",
            )
