"""Aba Social: renda, desigualdade e pobreza (Ipea, 1995 × 2024) e educação."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from painel import dados as d
from painel import visual as v

AREAS_PISA = ["Matemática", "Leitura", "Ciências"]


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

    mostra_pisa(edu, inicio, fim, tipos)

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


def mostra_pisa(edu: pd.DataFrame, inicio: int, fim: int, tipos: list[str]) -> None:
    """Pisa de 2000 a 2025: Brasil × média da OCDE, um gráfico por área."""
    c = v.cores()
    pisa = d.filtra_tipos(d.filtra_periodo(d.tabela("pisa_historico"), inicio, fim), tipos)
    if pisa.empty:
        return
    st.markdown("### Pisa: desempenho em 25 anos")
    ultimo = int(pisa["ano"].max())
    cartoes = []
    for area in AREAS_PISA:
        br_area = pisa[(pisa["area"] == area) & (pisa["grupo"] == "Brasil")].sort_values("ano")
        ocde = pisa[(pisa["area"] == area) & (pisa["grupo"] == "Média OCDE") & (pisa["ano"] == ultimo)]
        if br_area.empty:
            continue
        atual, primeiro = br_area.iloc[-1], br_area.iloc[0]
        detalhe = f"{int(primeiro['valor'])} em {int(primeiro['ano'])}"
        if not ocde.empty:
            detalhe += f" · média OCDE {int(ocde['valor'].iloc[0])}"
        cartoes.append({"rotulo": f"{area}, Pisa {int(atual['ano'])}", "valor": str(int(atual["valor"])),
                        "unidade": "pontos", "detalhe": detalhe, "destaque": area == "Matemática"})
    v.kpis(cartoes)

    colunas = st.columns(3)
    for coluna, area in zip(colunas, AREAS_PISA):
        dados_area = pisa[pisa["area"] == area]
        if dados_area.empty:
            continue
        with coluna:
            fig = go.Figure()
            for grupo, cor, largura in [("Média OCDE", c["neutro"], 2), ("Brasil", c["brasil"], 3)]:
                g = dados_area[dados_area["grupo"] == grupo].sort_values("ano")
                if g.empty:
                    continue
                fig.add_scatter(
                    x=g["ano"], y=g["valor"], name=grupo, mode="lines+markers+text",
                    line=dict(color=cor, width=largura, dash="dot" if grupo == "Média OCDE" else "solid"),
                    marker=dict(size=8, color=cor, symbol=["circle" if t == "oficial" else "circle-open"
                                                           for t in g["tipo"]], line=dict(width=2)),
                    text=[str(int(x)) if a in (g["ano"].min(), g["ano"].max()) else "" for a, x in zip(g["ano"], g["valor"])],
                    textposition="top center", textfont=dict(size=11),
                    hovertemplate="%{x}: %{y} pontos<extra>" + grupo + "</extra>",
                )
            v.estilo(fig, altura=300, titulo=area, legenda=area == "Matemática")
            fig.update_yaxes(range=[320, 530])
            fig.update_xaxes(range=[1998.5, 2026.5], dtick=5)
            fig.update_layout(legend=dict(y=-0.12, yanchor="top"), margin=dict(t=48))
            v.mostra(fig, dados_area.sort_values(["grupo", "ano"]), f"pisa_{area.lower()}")

    extra = edu[edu["indicador"].str.startswith("Pisa –")]
    v.leitura(
        "A nota brasileira subiu entre 2000 e 2009 e depois ficou estável. Como a média da OCDE caiu, sobretudo "
        "depois de 2018, a distância diminuiu: pelas contas do Inep (com outra média da OCDE, só dos países comparáveis), de 2006 a 2025 ela passou de **131 para 92 pontos** "
        "em matemática, de **102 para 58** em leitura e de **113 para 77** em ciências. Mesmo assim, o Brasil segue "
        "entre os últimos colocados."
        + (" No Pisa 2022, **" + v.br(float(extra[extra["indicador"].str.contains("leitura")]["valor"].iloc[0]), 0)
           + "%** dos alunos ficaram abaixo do nível básico em leitura." if not extra.empty else "")
    )
    v.nota("Leitura começa em 2000, matemática em 2003 e ciências em 2006: são os primeiros anos comparáveis de "
           "cada área. As médias da OCDE até 2022 são as publicadas em cada edição (o grupo de países muda); a de "
           "2025 usa o conjunto comparável do relatório de 2025. Pontos vazados: série histórica ainda não "
           "reconferida na fonte (Brasil em 2015 e médias da OCDE de 2000 a 2015).")
