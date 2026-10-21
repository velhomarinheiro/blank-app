"""Aba Poder de compra: salário mínimo × cesta básica, carne, gasolina, energia e itens da cesta."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from painel import carga
from painel import dados as d
from painel import visual as v


def mostra(inicio: int, fim: int, tipos: list[str]) -> None:
    c = v.cores()
    cesta = d.tabela("itens_cesta_destaques")

    def cv(item, indicador):
        return d.valor(cesta, item=item, indicador=indicador)

    ultimo = d.tabela("salario_minimo_cestas_sp").sort_values("ano").iloc[-1]
    v.kpis([
        {"rotulo": f"Salário mínimo {int(ultimo['ano'])}", "valor": f"R$ {v.br(ultimo['salario_minimo_rs'], 0)}",
         "detalhe": f"reajuste de {v.br(cv('Salário mínimo', 'reajuste 2025→2026'), 2)}%", "destaque": True},
        {"rotulo": "Cesta básica em São Paulo (ago/2026)", "valor": f"R$ {v.br(cv('Cesta básica São Paulo', 'custo'), 2)}",
         "detalhe": f"{v.br(cv('Cesta básica São Paulo', '% do salário mínimo'), 1)}% do salário mínimo", "tipo": None},
        {"rotulo": "Peso da carne no custo da cesta", "valor": v.br(cv("Carne", "participação no custo da cesta"), 1),
         "unidade": "%", "detalhe": "cerca de 1/3: R$ 303 por 6 kg", "tipo": "calculo"},
        {"rotulo": "Leite por salário mínimo (2026)",
         "valor": v.br(d.valor(cesta, item="Leite", periodo="2026"), 0), "unidade": "litros",
         "detalhe": f"eram {v.br(d.valor(cesta, item='Leite', periodo='2004'), 0)} em 2004", "tipo": "estimativa"},
    ])

    # ------------------------------------------------------------ Cestas por salário
    st.markdown("### Quantas cestas básicas o salário mínimo compra")
    sal = d.filtra_periodo(d.tabela("salario_minimo_cestas_sp"), inicio, fim)
    sal = d.filtra_tipos(sal, tipos)
    if not sal.empty:
        media = sal["referencia"].fillna("").str.startswith("media_anual")
        cor = [c["brasil"] if m else c["serie"][0] for m in media]
        opac = [0.5 if t == "calculo" else 1.0 for t in sal["tipo"]]
        fig = go.Figure(go.Bar(
            x=sal["ano"], y=sal["cestas_por_salario"], marker=dict(color=cor, opacity=opac),
            customdata=sal[["salario_minimo_rs", "referencia"]].fillna("—"),
            hovertemplate="%{x}: %{y:.2f} cestas<br>salário: R$ %{customdata[0]:,.0f}<br>%{customdata[1]}<extra></extra>",
            text=[v.br(x, 2) if x == x else "" for x in sal["cestas_por_salario"]], textposition="outside",
            textfont=dict(size=10), showlegend=False,
        ))
        if 2019 in set(sal["ano"]):
            fig.add_annotation(x=2019, y=0.15, text="sem dado", showarrow=False, textangle=-90, font=dict(size=10),
                               opacity=0.7)
        # Legenda manual para as duas cores.
        fig.add_scatter(x=[None], y=[None], mode="markers", marker=dict(size=10, color=c["brasil"], symbol="square"),
                        name="média anual")
        fig.add_scatter(x=[None], y=[None], mode="markers", marker=dict(size=10, color=c["serie"][0], symbol="square"),
                        name="mês de referência")
        v.estilo(fig, altura=360, eixo_y="cestas por salário")
        fig.update_yaxes(range=[0, sal["cestas_por_salario"].max() * 1.18])
        v.mostra(fig, sal, "cestas_por_salario")
        v.leitura(
            "O salário mínimo comprava **uma cesta** paulistana em 1995 e passou de **duas** entre 2009 e 2018. "
            "Com a alta dos alimentos na pandemia, caiu para cerca de 1,6 em 2020–2021 e voltou a "
            "**1,8 cesta** em 2026."
        )
        v.nota("Cesta de São Paulo (DIEESE), em geral a mais cara do país. 2019 ficou sem dado localizado e não foi "
               "interpolado. Anos em azul usam um mês de referência; barras claras são cálculo próprio.")

    col1, col2 = st.columns(2)
    # ------------------------------------------------------------ Carne
    with col1:
        carne = d.filtra_tipos(d.filtra_periodo(d.tabela("carne_kg_por_salario"), inicio, fim), tipos)
        if not carne.empty:
            fig = go.Figure()
            for i, (corte, grupo) in enumerate(carne.groupby("corte", sort=False)):
                cor = c["brasil"] if corte == "picanha" else c["serie"][i % len(c["serie"])]
                fig.add_scatter(
                    x=grupo["ano"], y=grupo["kg_por_salario"], name=corte,
                    mode="lines+markers" if len(grupo) > 2 else "markers",
                    line=dict(color=cor, width=2),
                    marker=dict(size=11, color=cor, symbol=[v.simbolo(t) for t in grupo["tipo"]], line=dict(width=2)),
                    customdata=grupo[["local", "tipo"]],
                    hovertemplate="%{x}: %{y:.1f} kg<br>%{customdata[0]} (%{customdata[1]})<extra>" + corte + "</extra>",
                )
            v.estilo(fig, altura=340, titulo="Carne: quilos por salário mínimo")
            fig.update_layout(legend=dict(y=-0.12, yanchor="top"), margin=dict(t=48))
            fig.update_yaxes(rangemode="tozero")
            v.mostra(fig, carne, "carne_por_salario")
            v.nota("Não há série anual contínua: o corte muda muito o resultado (acém compra o dobro da picanha).")
    # ------------------------------------------------------------ Gasolina
    with col2:
        gas = d.tabela("gasolina_energia_por_salario")
        gas = d.filtra_tipos(d.filtra_periodo(gas[gas["item"] == "gasolina"], inicio, fim), tipos)
        if not gas.empty:
            fig = go.Figure(go.Scatter(
                x=gas["ano"], y=gas["quantidade_por_salario"], mode="lines+markers",
                line=dict(color=c["serie"][0], width=2),
                marker=dict(size=11, color=c["serie"][0], symbol=[v.simbolo(t) for t in gas["tipo"]], line=dict(width=2)),
                customdata=gas[["referencia", "tipo"]],
                hovertemplate="%{x}: %{y:.0f} litros<br>%{customdata[0]} (%{customdata[1]})<extra></extra>",
            ))
            v.estilo(fig, altura=340, titulo="Gasolina: litros por salário mínimo", legenda=False)
            fig.update_yaxes(rangemode="tozero")
            v.mostra(fig, gas, "gasolina_por_salario")
            v.nota("Sem série confiável antes de 2002. Losangos vazados são estimativas; círculos vazados, cálculo "
                   "com preço médio da ANP.")

    mostra_inflacao_alimentos(inicio, fim, tipos)

    # ------------------------------------------------------------ Itens da cesta
    col1, col2 = st.columns(2)
    with col1:
        var = cesta[cesta["indicador"] == "variação 12 meses"].sort_values("valor")
        fig = go.Figure(go.Bar(
            y=var["item"], x=var["valor"], orientation="h",
            marker_color=[c["negativo"] if x > 0 else c["positivo"] for x in var["valor"]],
            text=[v.br(x, 1, sinal=True) + "%" for x in var["valor"]], textposition="outside",
            hovertemplate="%{y}: %{x:+.1f}%<extra></extra>",
        ))
        v.estilo(fig, altura=300, titulo="Preços em 12 meses (ago/25 → ago/26, SP)", legenda=False)
        fig.update_xaxes(showticklabels=False, range=[var["valor"].min() * 2.2, var["valor"].max() * 1.35])
        v.mostra(fig, var, "itens_cesta_variacao")
    # ------------------------------------------------------------ Energia
    with col2:
        en = d.tabela("energia_tarifa_notas")
        alta = d.valor(en, indicador="Alta da tarifa residencial (%)")
        ipca = d.valor(en, indicador="IPCA acumulado (%)")
        fig = go.Figure(go.Bar(
            x=["Tarifa residencial", "IPCA"], y=[alta, ipca], marker_color=[c["brasil"], c["neutro"]],
            text=[f"+{v.br(alta, 0)}%", f"+{v.br(ipca, 0)}%"], textposition="outside",
            hovertemplate="%{x}: +%{y:.0f}%<extra>2010–2024</extra>",
        ))
        v.estilo(fig, altura=300, titulo="Energia: alta acumulada 2010–2024", legenda=False)
        fig.update_yaxes(showticklabels=False, range=[0, alta * 1.2])
        v.mostra(fig, en, "energia_tarifa")
    kwh = d.tabela("gasolina_energia_por_salario")
    kwh = kwh[kwh["item"].str.startswith("energia")]
    v.leitura(
        f"A tarifa de luz subiu **{v.br(alta, 0)}%** de 2010 a 2024, acima do IPCA (**{v.br(ipca, 0)}%**). Mesmo assim, "
        f"como o salário mínimo subiu mais, ele pagava **{v.br(kwh.iloc[0]['quantidade_por_salario'], 0)} kWh** em 2012 "
        f"e **{v.br(kwh.iloc[1]['quantidade_por_salario'], 0)} kWh** em 2022 (cálculo com tarifa média do Instituto "
        "Acende Brasil)."
    )


PADRAO_ITENS = ["Alimentação no domicílio", "Arroz", "Feijão-carioca", "Café moído", "Leite longa vida"]


def mostra_inflacao_alimentos(inicio: int, fim: int, tipos: list[str]) -> None:
    """Variação anual do IPCA por item de alimentação, com o índice geral como referência."""
    c = v.cores()
    st.markdown("### Inflação dos alimentos, ano a ano (IPCA)")
    tabela, origem = carga.ipca_itens()
    tabela = d.filtra_tipos(d.filtra_periodo(tabela, inicio, fim), tipos)
    opcoes = [i for i in tabela["item"].drop_duplicates() if i != "Índice geral"]
    if not opcoes:
        st.info("Sem dados de inflação por item no período e nos tipos escolhidos.")
        return
    escolhidos = st.multiselect(
        "Itens (até 5)", opcoes, default=[i for i in PADRAO_ITENS if i in opcoes][:5] or opcoes[:5],
        max_selections=5, key="ipca_itens",
    )
    fig = go.Figure()
    geral = tabela[tabela["item"] == "Índice geral"].sort_values("ano")
    if not geral.empty:
        fig.add_scatter(x=geral["ano"], y=geral["variacao_pct"], name="IPCA geral", mode="lines",
                        line=dict(color=c["neutro"], width=2, dash="dot"),
                        hovertemplate="%{x}: %{y:.2f}%<extra>IPCA geral</extra>")
    for i, item in enumerate(escolhidos):  # a cor segue o item pela ordem de escolha
        g = tabela[tabela["item"] == item].sort_values("ano")
        if g.empty:
            continue
        # Anos sem dado ficam como lacuna, sem ligar os pontos.
        anos = pd.DataFrame({"ano": range(int(g["ano"].min()), int(g["ano"].max()) + 1)}).merge(g, how="left")
        fig.add_scatter(x=anos["ano"], y=anos["variacao_pct"], name=item, mode="lines+markers",
                        connectgaps=False, line=dict(color=c["serie"][i], width=2), marker=dict(size=8),
                        hovertemplate="%{x}: %{y:+.1f}%<extra>" + item + "</extra>")
    v.estilo(fig, altura=400, eixo_y="variação no ano (%)")
    fig.update_layout(hovermode="x unified", legend=dict(y=-0.12, yanchor="top"))
    anos_dados = tabela["ano"].max() - tabela["ano"].min()
    fig.update_xaxes(dtick=1 if anos_dados <= 15 else 2)
    fig.add_hline(y=0, line_width=1, line_color=c["neutro_claro"])
    v.mostra(fig, tabela.pivot_table(index="ano", columns="item", values="variacao_pct").reset_index(),
             "ipca_alimentos")
    v.leitura(
        "Os alimentos oscilam muito mais que o índice geral. O **arroz** subiu 76% em 2020 e caiu 27% em 2025; "
        "o **café moído** acumulou altas de 50% em 2021, 40% em 2024 e 36% em 2025; o **leite longa vida** subiu "
        "27% em 2020 e 26% em 2022."
    )
    v.nota(f"Variação acumulada de janeiro a dezembro de cada ano, Brasil. Fonte: {origem}.")
