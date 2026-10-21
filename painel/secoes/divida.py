"""Dívida pública: Brasil × outros países (FMI) e a série mensal brasileira (Banco Central)."""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from painel import carga
from painel import dados as d
from painel import fontes_abertas as fa
from painel import visual as v

PADRAO = ["Argentina", "México", "China", "Estados Unidos", "Itália"]
MEDIAS = ["Mundo", "Economias avançadas", "Emergentes e em desenvolvimento"]


def mostra(inicio: int, fim: int, tipos: list[str]) -> None:
    mostra_bcb(inicio, fim)
    mostra_comparacao(inicio)


def mostra_bcb(inicio: int, fim: int) -> None:
    """Dívida bruta e líquida mês a mês, se o Banco Central responder."""
    c = v.cores()
    serie, origem = carga.bcb_divida()
    if serie.empty:
        return
    serie = serie[serie["data"].dt.year.between(inicio, fim)]
    if serie.empty:
        return
    st.markdown("### Dívida bruta e líquida, mês a mês (% do PIB)")
    fig = go.Figure()
    for i, (nome, g) in enumerate(serie.groupby("serie", sort=False)):
        g = g.sort_values("data")
        cor = c["brasil"] if i == 0 else c["serie"][0]
        fig.add_scatter(x=g["data"], y=g["valor"], name=nome, mode="lines", line=dict(color=cor, width=2),
                        hovertemplate="%{x|%m/%Y}: %{y:.1f}% do PIB<extra>" + nome + "</extra>")
        ult = g.iloc[-1]
        fig.add_annotation(x=ult["data"], y=ult["valor"], text=f"{v.br(ult['valor'], 1)}%", showarrow=False,
                           xanchor="left", xshift=6, font=dict(color=cor, size=12))
    v.estilo(fig, altura=340)
    fig.update_layout(hovermode="x unified", margin=dict(r=50))
    fig.update_yaxes(rangemode="tozero")
    v.mostra(fig, serie.assign(data=serie["data"].dt.strftime("%Y-%m")).pivot_table(
        index="data", columns="serie", values="valor").reset_index(), "bcb_divida_mensal")
    v.nota(f"Dívida bruta do governo geral (série 13762) e dívida líquida do setor público consolidado (série 4513). "
           f"Fonte: {origem}.")


def mostra_comparacao(inicio: int) -> None:
    c = v.cores()
    st.markdown("### Dívida e resultado fiscal: Brasil e outros países")
    tabela, origem = carga.fmi()
    if tabela.empty:
        reserva()
        return
    v.leitura(
        "Dados do **Fiscal Monitor / World Economic Outlook do FMI** para o governo geral (União, estados e "
        "municípios), no mesmo conceito para todos os países. Anos à frente são projeções do FMI (linha tracejada)."
    )
    disponiveis = [k for k in fa.FMI_INDICADORES if k in set(tabela["indicador"])]
    col1, col2 = st.columns([2, 3])
    with col1:
        codigo = st.selectbox("Indicador", disponiveis, format_func=lambda k: fa.FMI_INDICADORES[k][0], key="fmi_ind")
    nomes = [n for k, (n, g) in fa.FMI_PAISES.items() if g not in ("Brasil", "Média")]
    with col2:
        escolhidos = st.multiselect("Comparar com (até 5)", nomes, default=PADRAO, max_selections=5, key="fmi_paises")
    col1, col2 = st.columns(2)
    with col1:
        com_medias = st.toggle("Médias (mundo, avançadas, emergentes) em cinza", value=True, key="fmi_medias")
    with col2:
        projecoes = st.toggle("Mostrar projeções do FMI", value=True, key="fmi_proj")

    nome, descricao = fa.FMI_INDICADORES[codigo]
    serie = tabela[(tabela["indicador"] == codigo) & (tabela["ano"] >= inicio)]
    if not projecoes:
        serie = serie[~serie["projecao"].astype(bool)]
    if serie.empty:
        st.info("Sem dados desse indicador no período escolhido.")
        return

    fig = go.Figure()

    def linha(pais, cor, largura, traco="solid", marcadores=False):
        g = serie[serie["pais"] == pais].sort_values("ano")
        if g.empty:
            return
        obs, proj = g[~g["projecao"].astype(bool)], g[g["projecao"].astype(bool)]
        if not obs.empty and not proj.empty:  # emenda a projeção no último ano observado
            proj = pd.concat([obs.tail(1), proj])
        for parte, tracejado, legenda in [(obs, traco, True), (proj, "dash", obs.empty)]:
            if parte.empty:
                continue
            fig.add_scatter(x=parte["ano"], y=parte["valor"], name=pais, legendgroup=pais, showlegend=legenda,
                            mode="lines+markers" if marcadores else "lines",
                            line=dict(color=cor, width=largura, dash=tracejado), marker=dict(size=5),
                            hovertemplate="%{x}: %{y:.1f}% do PIB<extra>" + pais + "</extra>")

    if com_medias:
        for i, m in enumerate(MEDIAS):
            linha(m, c["neutro"], 1.5, ["dot", "dashdot", "longdash"][i])
    for i, p in enumerate(escolhidos):
        linha(p, c["serie"][i], 2)
    linha("Brasil", c["brasil"], 3.5, marcadores=True)
    ano_atual = date.today().year - 1
    if projecoes and serie["projecao"].astype(bool).any():
        fig.add_vrect(x0=ano_atual + 0.5, x1=serie["ano"].max() + 0.5, fillcolor=c["faixa"], line_width=0, layer="below")
        fig.add_annotation(x=ano_atual + 0.5, y=1, yref="paper", text="projeção", showarrow=False, xanchor="left",
                           yanchor="bottom", font=dict(size=11), opacity=0.7)
    v.estilo(fig, altura=440, titulo=f"{nome} (% do PIB)")
    fig.update_layout(hovermode="x unified", legend=dict(y=-0.1, yanchor="top"))
    if codigo in ("GGXONLB_NGDP", "GGXCNL_NGDP"):
        fig.add_hline(y=0, line_width=1, line_color=c["neutro_claro"])
    v.mostra(fig, serie.pivot_table(index="ano", columns="pais", values="valor").reset_index().round(2),
             f"fmi_{codigo}")
    v.nota(f"{descricao} Fonte: {origem}.")

    # Ranking num ano à escolha.
    anos = sorted(serie["ano"].unique())
    padrao = ano_atual if ano_atual in anos else anos[-1]
    ano = st.select_slider("Ano do ranking", options=anos, value=padrao, key="fmi_ano")
    rk = serie[serie["ano"] == ano].sort_values("valor")
    if len(rk) > 2:
        cor_pais = {p: c["serie"][i] for i, p in enumerate(escolhidos)}
        cor = [c["brasil"] if p == "Brasil" else cor_pais.get(p, c["neutro_claro"] if g == "Média" else c["neutro"])
               for p, g in zip(rk["pais"], rk["grupo"])]
        fig = go.Figure(go.Bar(
            y=rk["pais"], x=rk["valor"], orientation="h", marker_color=cor,
            marker_pattern=dict(shape=["/" if g == "Média" else "" for g in rk["grupo"]], solidity=0.3, size=6),
            text=[v.br(x, 1) for x in rk["valor"]], textposition="outside",
            hovertemplate="%{y}: %{x:.1f}% do PIB<extra></extra>",
        ))
        projetado = " (projeção)" if rk["projecao"].astype(bool).any() else ""
        v.estilo(fig, altura=max(320, 24 * len(rk) + 60), titulo=f"{nome}, {ano}{projetado}", legenda=False)
        fig.update_xaxes(showticklabels=False, range=[min(0, rk["valor"].min() * 1.2), max(0, rk["valor"].max()) * 1.15 + 1])
        fig.update_yaxes(zeroline=False)
        v.mostra(fig, rk[["pais", "grupo", "ano", "valor", "projecao"]], f"fmi_ranking_{codigo}")
        so_paises = rk[rk["grupo"] != "Média"].sort_values("valor", ascending=False).reset_index(drop=True)
        if "Brasil" in set(so_paises["pais"]):
            pos = int(so_paises.index[so_paises["pais"] == "Brasil"][0]) + 1
            v.frase(f"Brasil: {pos}º maior valor entre {len(so_paises)} países desta lista em {ano} "
                    f"({v.br(float(so_paises.loc[pos - 1, 'valor']), 1)}% do PIB).")


def reserva() -> None:
    """Sem acesso ao FMI: mostra os pontos de comparação conferidos que vêm no pacote."""
    dest = d.tabela("divida_internacional_destaques")
    v.kpis([
        {"rotulo": f"{r['pais']} ({int(r['ano'])})", "valor": v.br(r["valor"], 1), "unidade": "% do PIB",
         "detalhe": r["indicador"], "destaque": r["pais"] == "Brasil"}
        for _, r in dest.iterrows()
    ])
    st.warning(
        "Não foi possível consultar o FMI agora. Os cartões acima mostram os pontos de comparação conferidos. "
        "Rode `python scripts/atualizar_dados_abertos.py` com internet para salvar a série completa em `data/`."
    )
    v.nota("Brasil no conceito do FMI, que inclui os títulos do Tesouro na carteira do Banco Central. Fontes: FMI "
           "(Fiscal Monitor e WEO de abril de 2026, Artigo IV dos EUA) e Banco Central.")
