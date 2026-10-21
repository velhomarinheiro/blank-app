"""Aba Tributação: carga tributária do Brasil comparada a outros países e sua composição."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from painel import dados as d
from painel import visual as v


def mostra(inicio: int, fim: int, tipos: list[str]) -> None:
    c = v.cores()
    paises = d.tabela("carga_tributaria_paises")
    comp = d.tabela("carga_tributaria_brasil_composicao")
    total = comp[comp["componente"] == "Carga total (Tesouro)"].sort_values("ano").iloc[-1]
    brasil = paises[paises["pais"] == "Brasil"].iloc[0]

    v.kpis([
        {"rotulo": f"Carga tributária {int(total['ano'])} (Tesouro)", "valor": v.br(total["pct_pib"], 1),
         "unidade": "% do PIB", "detalhe": "governo geral, metodologia nacional", "destaque": True},
        {"rotulo": f"Carga tributária {int(brasil['ano'])} (OCDE)", "valor": v.br(brasil["carga_pct_pib"], 1),
         "unidade": "% do PIB", "detalhe": "metodologia OCDE, comparável entre países"},
        {"rotulo": "Média da OCDE (2024)", "valor": v.br(d.valor(paises.rename(columns={"carga_pct_pib": "valor"}),
                                                                  pais="Média OCDE"), 1),
         "unidade": "% do PIB"},
        {"rotulo": "Média da América Latina (2024)",
         "valor": v.br(d.valor(paises.rename(columns={"carga_pct_pib": "valor"}),
                               pais="Média América Latina e Caribe"), 1), "unidade": "% do PIB"},
    ])

    st.markdown("### Carga tributária: Brasil e outros países (% do PIB)")
    grupos = st.multiselect(
        "Grupos", ["Europa", "EUA", "Emergente", "Média"], default=["Europa", "EUA", "Emergente", "Média"],
        key="grupos_carga", label_visibility="collapsed", placeholder="Escolha os grupos de países",
    )
    tabela = paises[(paises["grupo"] == "Brasil") | paises["grupo"].isin(grupos)].sort_values("carga_pct_pib")
    cor = [c["brasil"] if g == "Brasil" else (c["neutro"] if g == "Média" else c["serie"][0]) for g in tabela["grupo"]]
    rotulos = [f"{p} ({a})" if a != 2024 else p for p, a in zip(tabela["pais"], tabela["ano"])]
    fig = go.Figure(go.Bar(
        y=rotulos, x=tabela["carga_pct_pib"], orientation="h", marker_color=cor,
        marker_pattern=dict(shape=["/" if g == "Média" else "" for g in tabela["grupo"]], solidity=0.3, size=6),
        text=[v.br(x, 1) for x in tabela["carga_pct_pib"]], textposition="outside",
        customdata=tabela[["grupo", "ano", "fonte_id"]],
        hovertemplate="%{y}: %{x:.1f}% do PIB<br>%{customdata[0]}, %{customdata[1]}<br>%{customdata[2]}<extra></extra>",
    ))
    v.estilo(fig, altura=max(320, 26 * len(tabela) + 40), legenda=False)
    fig.update_xaxes(showticklabels=False, range=[0, tabela["carga_pct_pib"].max() * 1.12])
    fig.update_yaxes(zeroline=False)
    v.mostra(fig, tabela, "carga_tributaria_paises")
    v.leitura(
        "O Brasil arrecada **mais que a média da OCDE** e bem mais que os vizinhos da América Latina e os EUA, "
        "mas menos que os países europeus de Estado de bem-estar amplo. Barras hachuradas são médias de grupos."
    )
    v.nota("Dados da OCDE de 2024 são preliminares. Argentina (2023) e África do Sul (2022) usam anos anteriores. "
           "A diferença entre 32,4% (Tesouro) e 33,7% (OCDE) vem de metodologias distintas.")

    # ------------------------------------------------------------ Composição
    st.markdown("### Quanto vem do consumo e quanto vem da renda")
    bens = comp[(comp["componente"] == "Bens e serviços") & (comp["ano"] == 2025)].iloc[0]
    renda = comp[(comp["componente"] == "Renda, lucros e ganhos de capital") & (comp["ano"] == 2025)].iloc[0]
    outros = 100 - bens["pct_da_arrecadacao"] - renda["pct_da_arrecadacao"]
    ocde = comp.set_index("componente")["pct_da_arrecadacao"]
    ocde_consumo = ocde["OCDE: IVA"] + ocde["OCDE: outros impostos sobre consumo"]
    ocde_renda = ocde["OCDE: IR pessoa física"] + ocde["OCDE: IR pessoa jurídica"]

    comparacao = pd.DataFrame({
        "estrutura": ["Brasil 2025", "Média OCDE"],
        "Consumo (bens e serviços)": [bens["pct_da_arrecadacao"], ocde_consumo],
        "Renda e lucros": [renda["pct_da_arrecadacao"], ocde_renda],
        "Demais (contribuições, patrimônio etc.)": [outros, 100 - ocde_consumo - ocde_renda],
    })
    fig = go.Figure()
    for i, col in enumerate(comparacao.columns[1:]):
        fig.add_bar(y=comparacao["estrutura"], x=comparacao[col], name=col, orientation="h",
                    marker=dict(color=[c["serie"][0], c["serie"][1], c["neutro"]][i], line=dict(width=2, color=c["fundo"])),
                    text=[v.br(x, 1) + "%" for x in comparacao[col]], textposition="inside", insidetextanchor="middle",
                    hovertemplate="%{y}: %{x:.1f}% da arrecadação<extra>" + col + "</extra>")
    v.estilo(fig, altura=230)
    fig.update_layout(barmode="stack", bargap=0.35, legend=dict(traceorder="normal"))
    fig.update_xaxes(showticklabels=False, range=[0, 100])
    fig.update_yaxes(autorange="reversed", zeroline=False)
    v.mostra(fig, comparacao.round(1), "composicao_carga")
    v.leitura(
        f"Cerca de **{v.br(bens['pct_da_arrecadacao'], 0)}%** da arrecadação brasileira vem de tributos sobre bens e "
        f"serviços, contra **{v.br(ocde_consumo, 0)}%** na média da OCDE (IVA e outros tributos sobre consumo). "
        f"A renda pesa {v.br(renda['pct_da_arrecadacao'], 0)}% aqui e {v.br(ocde_renda, 0)}% na OCDE. Tributos "
        "sobre consumo pesam mais, proporcionalmente, no orçamento das famílias de renda baixa."
    )
    v.nota("Cálculo próprio. Brasil: Tesouro Nacional, 2025. OCDE: IVA, outros consumo e IR pessoa jurídica de 2022; "
           "IR pessoa física de 2023 (Revenue Statistics). Anos diferentes: compare só a ordem de grandeza.")
