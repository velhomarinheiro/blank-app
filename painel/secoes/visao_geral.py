"""Aba Visão geral: indicadores-chave, PIB e inflação com as fases do período."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from painel import dados as d
from painel import visual as v

# Fases do período (rótulo, primeiro ano, último ano). 2021, ano da retomada pós-pandemia, fica na última fase.
FASES = [
    ("Estabilização", 1995, 2002),
    ("Crescimento com inclusão", 2003, 2014),
    ("Crises", 2015, 2020),
    ("Retomada", 2021, 2025),
]


def faixas(fig: go.Figure, inicio: int, fim: int, rotulos: bool = True) -> None:
    """Faixas alternadas no fundo marcando as quatro fases."""
    for i, (nome, a, b) in enumerate(FASES):
        a, b = max(a, inicio), min(b, fim)
        if a > b:
            continue
        fig.add_vrect(
            x0=a - 0.5, x1=b + 0.5, line_width=0, layer="below",
            fillcolor=v.cores()["faixa"] if i % 2 == 0 else "rgba(0,0,0,0)",
        )
        if rotulos:
            fig.add_annotation(
                x=(a + b) / 2, y=1.0, yref="paper", yanchor="bottom", text=nome.split()[0], showarrow=False,
                font=dict(size=11), opacity=0.7,
            )


def mostra(inicio: int, fim: int, tipos: list[str]) -> None:
    c = v.cores()
    ind = d.tabela("indicadores_chave")

    def iv(nome, ref=None):
        linhas = ind[ind["indicador"] == nome]
        if ref is not None:
            linhas = linhas[linhas["referencia"].astype(str) == str(ref)]
        return float(linhas.iloc[0]["valor"])

    v.kpis([
        {"rotulo": "PIB nominal 2025", "valor": f"R$ {v.br(iv('PIB nominal'), 1)}", "unidade": "tri",
         "detalhe": f"crescimento real de {v.br(iv('Crescimento real do PIB'), 1)}%", "destaque": True},
        {"rotulo": "PIB per capita 2025", "valor": f"R$ {v.br(iv('PIB per capita'), 0)}",
         "detalhe": "IBGE, Contas Nacionais"},
        {"rotulo": "Inflação (IPCA) 2025", "valor": v.br(iv("IPCA"), 2), "unidade": "%",
         "detalhe": "dentro do intervalo da meta (até 4,5%)"},
        {"rotulo": "Desemprego 2025", "valor": v.br(iv("Taxa de desocupação (média anual)"), 1), "unidade": "%",
         "detalhe": "média anual, PNAD Contínua"},
        {"rotulo": "IDH 2023", "valor": v.br(iv("IDH"), 3),
         "detalhe": f"{int(iv('IDH posição'))}ª posição entre 193 países"},
        {"rotulo": "Expectativa de vida 2024", "valor": v.br(iv("Expectativa de vida ao nascer", 2024), 1),
         "unidade": "anos", "detalhe": f"era {v.br(iv('Expectativa de vida ao nascer', 2021), 1)} em 2021 (pandemia)"},
        {"rotulo": "Mortalidade infantil 2024", "valor": v.br(iv("Mortalidade infantil"), 1),
         "detalhe": "por mil nascidos vivos"},
        {"rotulo": "Pobreza 2024 (IBGE)", "valor": v.br(iv("Pobreza (critério IBGE)"), 1), "unidade": "%",
         "detalhe": f"extrema pobreza: {v.br(iv('Extrema pobreza (critério IBGE)'), 1)}%"},
    ])

    macro = d.filtra_periodo(d.tabela("macro_pib_ipca_anual"), inicio, fim)
    macro = d.filtra_tipos(macro, tipos)
    if macro.empty:
        st.info("Nenhum dado de PIB e IPCA no período e nos tipos escolhidos.")
        return

    st.markdown("### Crescimento do PIB e inflação, ano a ano")
    v.leitura(
        "As faixas marcam quatro fases: a **estabilização** pós-Real (1995–2002), o **crescimento com inclusão** "
        "(2003–2014), as **crises** de 2015–2016 e da pandemia (2015–2020) e a **retomada** (2021–2025). "
        "Os dois gráficos usam escalas próprias, um abaixo do outro, para não misturar eixos."
    )

    fig = go.Figure(go.Bar(
        x=macro["ano"], y=macro["pib_crescimento_real_pct"],
        marker_color=[c["positivo"] if y >= 0 else c["negativo"] for y in macro["pib_crescimento_real_pct"]],
        hovertemplate="%{x}: %{y:.1f}%<extra>PIB</extra>",
        marker_line_width=0,
    ))
    faixas(fig, inicio, fim)
    v.estilo(fig, altura=320, titulo="PIB: crescimento real (% ao ano)", legenda=False)
    fig.update_layout(margin=dict(t=64))
    fig.update_xaxes(range=[macro["ano"].min() - 0.6, macro["ano"].max() + 0.6])
    v.mostra(fig)

    fig = go.Figure(go.Scatter(
        x=macro["ano"], y=macro["ipca_anual_pct"], mode="lines+markers",
        line=dict(color=c["serie"][0], width=2), marker=dict(size=7),
        hovertemplate="%{x}: %{y:.2f}%<extra>IPCA</extra>",
    ))
    faixas(fig, inicio, fim, rotulos=False)
    v.estilo(fig, altura=280, titulo="IPCA: inflação anual (%)", legenda=False)
    fig.update_xaxes(range=[macro["ano"].min() - 0.6, macro["ano"].max() + 0.6])
    v.mostra(fig, macro.rename(columns={"pib_crescimento_real_pct": "PIB (% real)", "ipca_anual_pct": "IPCA (%)"}),
             "pib_ipca")

    # Médias por fase: crescimento médio composto e IPCA médio.
    linhas = []
    for nome, a, b in FASES:
        trecho = macro[macro["ano"].between(a, b)]
        if trecho.empty:
            continue
        pib = ((1 + trecho["pib_crescimento_real_pct"] / 100).prod() ** (1 / len(trecho)) - 1) * 100
        ipca = ((1 + trecho["ipca_anual_pct"] / 100).prod() ** (1 / len(trecho)) - 1) * 100
        linhas.append({"Fase": f"{nome} ({int(trecho['ano'].min())}–{int(trecho['ano'].max())})",
                       "PIB: média anual (%)": round(pib, 1), "IPCA: média anual (%)": round(ipca, 1)})
    if linhas:
        st.markdown("### Médias por fase")
        tabela = pd.DataFrame(linhas)
        fig = go.Figure()
        fig.add_bar(y=tabela["Fase"], x=tabela["PIB: média anual (%)"], orientation="h", name="PIB",
                    marker_color=c["serie"][0], hovertemplate="%{x:.1f}%<extra>PIB</extra>",
                    text=[v.br(x) + "%" for x in tabela["PIB: média anual (%)"]], textposition="outside", cliponaxis=False)
        fig.add_bar(y=tabela["Fase"], x=tabela["IPCA: média anual (%)"], orientation="h", name="IPCA",
                    marker_color=c["serie"][1], hovertemplate="%{x:.1f}%<extra>IPCA</extra>",
                    text=[v.br(x) + "%" for x in tabela["IPCA: média anual (%)"]], textposition="outside")
        v.estilo(fig, altura=300)
        fig.update_layout(bargroupgap=0.08)
        fig.update_yaxes(autorange="reversed", zeroline=False)
        fig.update_xaxes(showticklabels=False, zeroline=True)
        v.mostra(fig, tabela, "medias_por_fase")
        v.nota("Médias geométricas dos anos de cada fase dentro do período escolhido. Cálculo próprio "
               "a partir das séries do IBGE.")
