"""Aba Social: renda, desigualdade e pobreza (Ipea, 1995 × 2024) e educação."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from painel import dados as d
from painel import visual as v

# Médias da OCDE no Pisa 2022 (relatório OCDE, volume I), usadas só como referência.
PISA_OCDE_2022 = {"Pisa matemática": 472, "Pisa leitura": 476, "Pisa ciências": 485}


def halteres(rotulos, antes, depois, ano_antes, ano_depois, unidade="", casas=1, altura=260):
    """Gráfico de halteres: dois pontos ligados por uma linha, um por ano."""
    c = v.cores()
    fig = go.Figure()
    for r, a, b in zip(rotulos, antes, depois):
        fig.add_trace(go.Scatter(x=[a, b], y=[r, r], mode="lines", line=dict(color=c["neutro_claro"], width=3),
                                 showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=antes, y=rotulos, mode="markers+text", name=str(ano_antes),
                             marker=dict(size=13, color=c["neutro"]),
                             text=[v.br(x, casas) for x in antes],
                             textposition=["middle left" if a < b else "middle right" for a, b in zip(antes, depois)],
                             hovertemplate=f"%{{y}} em {ano_antes}: %{{x}}{unidade}<extra></extra>"))
    fig.add_trace(go.Scatter(x=depois, y=rotulos, mode="markers+text", name=str(ano_depois),
                             marker=dict(size=13, color=c["brasil"]),
                             text=[v.br(x, casas) for x in depois],
                             textposition=["middle right" if a < b else "middle left" for a, b in zip(antes, depois)],
                             hovertemplate=f"%{{y}} em {ano_depois}: %{{x}}{unidade}<extra></extra>"))
    v.estilo(fig, altura=altura)
    fig.update_yaxes(autorange="reversed", zeroline=False)
    fig.update_xaxes(showgrid=True, zeroline=False)
    span = max(max(antes), max(depois)) - min(min(antes), min(depois))
    fig.update_xaxes(range=[min(min(antes), min(depois)) - span * 0.25, max(max(antes), max(depois)) + span * 0.25])
    return fig


def mostra(inicio: int, fim: int, tipos: list[str]) -> None:
    c = v.cores()
    ipea = d.tabela("renda_pobreza_desigualdade_ipea")
    ind = d.tabela("indicadores_chave")

    st.markdown("### Renda, desigualdade e pobreza: 1995 × 2024")
    renda = ipea.iloc[0]
    v.kpis([
        {"rotulo": "Renda domiciliar per capita (R$ de 2024)", "valor": f"R$ {v.br(renda['valor_2024'], 0)}",
         "detalhe": f"R$ {v.br(renda['valor_1995'], 0)} em 1995: {renda['variacao']}", "destaque": True},
        {"rotulo": "Gini 2024 (Ipea, 0–100)", "valor": v.br(ipea.iloc[1]["valor_2024"], 1),
         "detalhe": f"{v.br(ipea.iloc[1]['valor_1995'], 1)} em 1995: queda de 18%"},
        {"rotulo": "Pobreza (US$ 8,30/dia)", "valor": v.br(ipea.iloc[2]["valor_2024"], 1), "unidade": "%",
         "detalhe": f"{v.br(ipea.iloc[2]['valor_1995'], 1)}% em 1995"},
        {"rotulo": "Extrema pobreza (US$ 3/dia)", "valor": v.br(ipea.iloc[3]["valor_2024"], 1), "unidade": "%",
         "detalhe": f"{v.br(ipea.iloc[3]['valor_1995'], 1)}% em 1995"},
    ])
    fig = halteres(["Gini (0–100)", "Pobreza (%)", "Extrema pobreza (%)"],
                   ipea["valor_1995"].iloc[1:].tolist(), ipea["valor_2024"].iloc[1:].tolist(), 1995, 2024)
    v.mostra(fig, ipea, "renda_pobreza_ipea")
    v.leitura(
        "Em três décadas, a renda real por pessoa subiu cerca de **69%**, a desigualdade caiu e a extrema pobreza "
        "passou de um quarto para menos de 5% da população. Pelo critério do IBGE, a pobreza em 2024 era de "
        f"**{v.br(d.valor(ind, indicador='Pobreza (critério IBGE)'), 1)}%** e o Gini, "
        f"**{v.br(d.valor(ind, indicador='Gini (IBGE)'), 3)}**."
    )
    v.nota("Linhas de pobreza do Ipea (PPC 2021) diferem das do IBGE. Até 2015 a fonte é a PNAD; depois, a PNAD "
           "Contínua: comparações longas são indicativas.")

    # ------------------------------------------------------------ Educação
    edu = d.filtra_tipos(d.tabela("educacao"), tipos)
    st.markdown("### Educação")

    anal = edu[(edu["indicador"] == "Analfabetismo 15+") & (edu["recorte"] == "Brasil")]
    sup = edu[edu["indicador"] == "Superior completo"]
    medio = edu[edu["indicador"] == "Ao menos ensino médio completo"]
    cartoes = []
    if not anal.empty:
        cartoes.append({"rotulo": f"Analfabetismo 15+ ({int(anal['ano'].max())})",
                        "valor": v.br(anal.sort_values("ano").iloc[-1]["valor"], 1), "unidade": "%",
                        "detalhe": f"{v.br(anal.sort_values('ano').iloc[0]['valor'], 1)}% em {int(anal['ano'].min())}",
                        "destaque": True})
    if not medio.empty:
        cartoes.append({"rotulo": "Ao menos ensino médio (25+), 2025", "valor": v.br(medio.iloc[0]["valor"], 1),
                        "unidade": "%"})
    if not sup.empty:
        cartoes.append({"rotulo": "Superior completo (25+), 2025",
                        "valor": v.br(sup.sort_values("ano").iloc[-1]["valor"], 1), "unidade": "%",
                        "detalhe": f"{v.br(sup.sort_values('ano').iloc[0]['valor'], 1)}% em 2016"})
    abandono = edu[edu["indicador"] == "Abandono por necessidade de trabalhar"]
    if not abandono.empty:
        cartoes.append({"rotulo": "Deixaram de estudar para trabalhar", "valor": v.br(abandono.iloc[0]["valor"], 0),
                        "unidade": "%", "detalhe": "dos jovens de 14 a 29 anos que pararam (2024)"})
    if cartoes:
        v.kpis(cartoes)

    col1, col2 = st.columns(2)
    with col1:
        rec = edu[(edu["ano"] == 2024) & edu["indicador"].str.startswith("Analfabetismo")]
        if not rec.empty:
            rec = rec.sort_values("valor")
            fig = go.Figure(go.Bar(
                y=rec["recorte"], x=rec["valor"], orientation="h",
                marker_color=[c["brasil"] if r in ("Nordeste", "60 anos ou mais", "Pretos e pardos") else c["neutro"]
                              for r in rec["recorte"]],
                text=[v.br(x, 1) + "%" for x in rec["valor"]], textposition="outside",
                hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
            ))
            v.estilo(fig, altura=300, titulo="Analfabetismo por recorte, 2024 (%)", legenda=False)
            fig.update_xaxes(showticklabels=False, range=[0, rec["valor"].max() * 1.25])
            v.mostra(fig, rec[["recorte", "valor", "tipo", "fonte_id"]], "analfabetismo_recortes")
    with col2:
        ideb = edu[edu["indicador"] == "Ideb"]
        if not ideb.empty and {2005, 2025} <= set(ideb["ano"]):
            etapas = ["Anos iniciais", "Anos finais", "Ensino médio"]
            antes = [float(ideb[(ideb["recorte"] == e) & (ideb["ano"] == 2005)]["valor"].iloc[0]) for e in etapas]
            depois = [float(ideb[(ideb["recorte"] == e) & (ideb["ano"] == 2025)]["valor"].iloc[0]) for e in etapas]
            fig = halteres(etapas, antes, depois, 2005, 2025, altura=300)
            v.estilo(fig, altura=300, titulo="Ideb: 2005 × 2025")
            fig.update_layout(legend=dict(y=-0.15, yanchor="top"))
            v.mostra(fig, ideb[["indicador", "recorte", "ano", "valor", "fonte_id"]], "ideb")

    pisa = edu[edu["indicador"].isin(PISA_OCDE_2022)]
    if not pisa.empty:
        fig = go.Figure()
        fig.add_bar(x=[i.replace("Pisa ", "").capitalize() for i in pisa["indicador"]], y=pisa["valor"],
                    name="Brasil", marker_color=c["brasil"], text=pisa["valor"].astype(int), textposition="outside",
                    hovertemplate="%{x}: %{y} pontos<extra>Brasil</extra>")
        fig.add_bar(x=[i.replace("Pisa ", "").capitalize() for i in PISA_OCDE_2022],
                    y=list(PISA_OCDE_2022.values()), name="Média OCDE", marker_color=c["neutro"],
                    text=list(PISA_OCDE_2022.values()), textposition="outside",
                    hovertemplate="%{x}: %{y} pontos<extra>Média OCDE</extra>")
        v.estilo(fig, altura=300, titulo="Pisa 2022: Brasil × média da OCDE (pontos)")
        fig.update_yaxes(range=[300, 520])
        fig.update_layout(bargroupgap=0.06)
        fig.update_layout(margin=dict(t=70))
        tabela = pisa[["indicador", "valor"]].assign(media_ocde=[PISA_OCDE_2022[i] for i in pisa["indicador"]])
        v.mostra(fig, tabela, "pisa_2022")
        extra = edu[edu["indicador"].str.startswith("Pisa –")]
        if not extra.empty:
            v.leitura("No Pisa 2022, **" + v.br(float(extra[extra['indicador'].str.contains('leitura')]['valor'].iloc[0]), 0)
                      + "%** dos alunos brasileiros ficaram abaixo do nível básico em leitura e só **"
                      + v.br(float(extra[extra['indicador'].str.contains('alto')]['valor'].iloc[0]), 0)
                      + "%** chegaram ao alto desempenho em matemática.")
        v.nota("Médias da OCDE do relatório Pisa 2022 (472 em matemática, 476 em leitura, 485 em ciências), "
               "incluídas como referência.")

    inv = edu[edu["indicador"].str.startswith(("Investimento", "Meta"))]
    cofog = d.tabela("despesas_por_funcao")
    cofog = cofog[cofog["funcao"] == "Educação"]
    if not inv.empty:
        serie = pd.concat([
            inv[inv["indicador"] == "Investimento público em educação"][["ano", "valor"]].assign(serie="Inep"),
            cofog.rename(columns={"pct_pib": "valor"})[["ano", "valor"]].assign(serie="Tesouro (COFOG)"),
        ])
        serie = d.filtra_periodo(serie, inicio, fim)
        metas = inv[inv["indicador"].str.startswith("Meta")]
        fig = go.Figure()
        for i, (nome, grupo) in enumerate(serie.groupby("serie", sort=False)):
            fig.add_scatter(x=grupo["ano"], y=grupo["valor"], mode="markers+lines", name=nome,
                            marker=dict(size=10, color=c["serie"][i]), line=dict(color=c["serie"][i], width=2),
                            hovertemplate="%{x}: %{y:.1f}% do PIB<extra>" + nome + "</extra>")
        for _, m in metas.iterrows():
            fig.add_scatter(x=[m["ano"]], y=[m["valor"]], mode="markers+text", name=m["indicador"],
                            marker=dict(size=12, symbol="diamond-open", color=c["neutro"]),
                            text=[f"{m['indicador']}: {v.br(m['valor'], 1)}%"], textposition="middle left",
                            showlegend=False, hovertemplate="%{y:.1f}% do PIB<extra>" + m["indicador"] + "</extra>")
        v.estilo(fig, altura=320, titulo="Gasto público em educação (% do PIB) e metas do PNE")
        fig.update_yaxes(range=[0, 11.5])
        fig.update_layout(margin=dict(t=70))
        v.mostra(fig, pd.concat([serie, metas[["ano", "valor"]].assign(serie=metas["indicador"])]), "educacao_gasto")
        v.nota("Inep e Tesouro (COFOG) medem o gasto de formas diferentes; os pontos não formam uma série única. "
               "A meta de 10% do PIB do PNE 2014–2024 não foi atingida.")
