"""Aba Contas públicas: resultado primário, dívida, juros e gasto por função."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from painel import dados as d
from painel import visual as v


def mostra(inicio: int, fim: int, tipos: list[str]) -> None:
    c = v.cores()
    dest = d.tabela("contas_publicas_destaques")

    def dv(indicador, unidade, periodo):
        return d.valor(dest, indicador=indicador, unidade=unidade, periodo=periodo)

    v.kpis([
        {"rotulo": "Déficit primário 2025 (gov. central)", "valor": v.br(dv("Déficit primário governo central", "% do PIB", "2025"), 2),
         "unidade": "% do PIB", "detalhe": f"R$ {v.br(dv('Déficit primário governo central', 'R$ bilhões', '2025'), 1)} bi",
         "destaque": True},
        {"rotulo": "Juros nominais 2025", "valor": v.br(dv("Juros nominais", "% do PIB", "2025"), 1),
         "unidade": "% do PIB", "detalhe": f"Selic chegou a {v.br(dv('Selic (pico)', '% a.a.', '2025'), 0)}% ao ano"},
        {"rotulo": "Dívida bruta (jul/2026)", "unidade": "% do PIB",
         "valor": v.br(d.tabela("contas_publicas_anual").set_index("ano").loc["jul/2026", "dbgg_dez_pct_pib"], 1),
         "detalhe": f"R$ {v.br(dv('DBGG', 'R$ trilhões', 'jul/2026'), 2)} tri; conceito FMI: "
                    f"{v.br(dv('DBGG conceito FMI', '% do PIB', 'jul/2026'), 1)}%"},
        {"rotulo": "Dívida líquida (jul/2026)", "valor": v.br(dv("DLSP", "% do PIB", "jul/2026"), 1),
         "unidade": "% do PIB", "detalhe": f"{v.br(dv('DLSP', '% do PIB', 'dez/2025'), 1)}% em dez/2025"},
        {"rotulo": "Déficit da Previdência (RGPS) 2025", "valor": f"R$ {v.br(dv('Déficit RGPS (Previdência)', 'R$ bilhões', '2025'), 1)}",
         "unidade": "bi"},
    ])

    anual = d.tabela("contas_publicas_anual")
    anual_num = anual[pd.to_numeric(anual["ano"], errors="coerce").notna()].copy()
    anual_num["ano"] = anual_num["ano"].astype(int)
    anual_num = d.filtra_periodo(anual_num, inicio, fim)

    col1, col2 = st.columns(2)
    with col1:
        prim = d.filtra_tipos(anual_num.dropna(subset=["resultado_primario_gov_central_pct_pib"]), tipos, "tipo_primario")
        y = prim["resultado_primario_gov_central_pct_pib"]
        fig = go.Figure(go.Bar(
            x=prim["ano"], y=y, marker_color=[c["positivo"] if x >= 0 else c["negativo"] for x in y],
            hovertemplate="%{x}: %{y:.2f}% do PIB<extra></extra>",
        ))
        v.estilo(fig, altura=320, titulo="Resultado primário do governo central (% do PIB)", legenda=False)
        if 2020 in set(prim["ano"]):
            fig.add_annotation(x=2020, y=-9.8, text="pandemia", showarrow=False, yanchor="top", font=dict(size=11))
        v.mostra(fig, prim[["ano", "resultado_primario_gov_central_pct_pib", "tipo_primario"]], "resultado_primario")
    with col2:
        div = d.filtra_tipos(anual.dropna(subset=["dbgg_dez_pct_pib"]), tipos, "tipo_dbgg").copy()
        div["ano_num"] = pd.to_numeric(div["ano"], errors="coerce").fillna(2026 + 6 / 12)
        div = div[div["ano_num"].between(inicio, fim + 0.99)]
        fig = go.Figure(go.Scatter(
            x=div["ano_num"], y=div["dbgg_dez_pct_pib"], mode="lines+markers",
            line=dict(color=c["brasil"], width=2), marker=dict(size=7),
            text=div["ano"].astype(str), hovertemplate="%{text}: %{y:.1f}% do PIB<extra></extra>",
        ))
        if not div.empty:
            ult = div.iloc[-1]
            fig.add_annotation(x=ult["ano_num"], y=ult["dbgg_dez_pct_pib"], text=f"{ult['ano']}: {v.br(ult['dbgg_dez_pct_pib'], 1)}%",
                               showarrow=False, yshift=14, xanchor="right", font=dict(size=11))
        v.estilo(fig, altura=320, titulo="Dívida bruta do governo geral (% do PIB, dezembro)", legenda=False)
        fig.update_yaxes(range=[40, 95])
        fig.update_xaxes(dtick=2)
        v.mostra(fig, div[["ano", "dbgg_dez_pct_pib", "tipo_dbgg"]], "divida_bruta")
    v.nota("Resultado primário do governo central (Tesouro + BC + Previdência); dívida bruta pelo conceito do Banco "
           "Central. Valores de 2010–2023 vêm de séries oficiais ainda não reconferidas ponto a ponto.")

    st.markdown("### O que fez a dívida líquida subir em 2025")
    contrib = pd.DataFrame({
        "fator": ["Juros", "Déficit primário"],
        "pp_pib": [dv("Contribuição dos juros à alta da DLSP", "p.p. do PIB", "2025"),
                   dv("Contribuição do déficit primário à alta da DLSP", "p.p. do PIB", "2025")],
    })
    fig = go.Figure(go.Bar(
        y=contrib["fator"], x=contrib["pp_pib"], orientation="h", marker_color=[c["brasil"], c["serie"][0]],
        text=[v.br(x, 1) + " p.p." for x in contrib["pp_pib"]], textposition="outside",
        hovertemplate="%{y}: %{x:.1f} p.p. do PIB<extra></extra>",
    ))
    v.estilo(fig, altura=170, legenda=False)
    fig.update_xaxes(showticklabels=False, range=[0, 9.5])
    fig.update_yaxes(zeroline=False, autorange="reversed")
    v.mostra(fig, contrib, "contribuicao_dlsp")
    v.leitura(
        "Os **juros** explicam quase toda a alta da dívida líquida em 2025: 7,9 pontos do PIB, contra 0,4 do déficit "
        "primário. Com a Selic em 15%, o déficit nominal em 12 meses chegou a "
        f"**{v.br(dv('Déficit nominal (12 meses)', '% do PIB', 'até jul/2026'), 2)}% do PIB** em julho de 2026."
    )

    # ------------------------------------------------------------ Gasto por função
    st.markdown("### Gasto por função: Brasil e referências internacionais (% do PIB)")
    func = d.tabela("despesas_por_funcao")
    pares = [
        ("Proteção social", "Proteção social", 2023, "Proteção social – média economias avançadas", "economias avançadas"),
        ("Defesa", "Defesa (SIPRI)", 2025, "Defesa – média mundial (SIPRI)", "média mundial"),
    ]
    linhas = []
    for rotulo, nome_br, ano_br, nome_ref, rotulo_ref in pares:
        b = func[(func["funcao"] == nome_br) & (func["ano"] == ano_br)].iloc[0]["pct_pib"]
        r = func[func["funcao"] == nome_ref].iloc[0]
        linhas.append({"função": rotulo, "Brasil": b, "referência": r["pct_pib"], "qual referência": f"{rotulo_ref} ({r['ano']})"})
    for nome in ["Saúde", "Educação", "Habitação e serviços comunitários"]:
        b = func[func["funcao"] == nome].sort_values("ano").iloc[-1]
        linhas.append({"função": nome, "Brasil": b["pct_pib"], "referência": None, "qual referência": ""})
    tabela = pd.DataFrame(linhas)
    fig = go.Figure()
    fig.add_bar(y=tabela["função"], x=tabela["Brasil"], name="Brasil", orientation="h", marker_color=c["brasil"],
                text=[v.br(x, 1) for x in tabela["Brasil"]], textposition="outside",
                hovertemplate="%{y}: %{x:.1f}% do PIB<extra>Brasil</extra>")
    fig.add_bar(y=tabela["função"], x=tabela["referência"], name="Referência internacional", orientation="h",
                marker_color=c["neutro"], customdata=tabela["qual referência"],
                text=[v.br(x, 1) if x == x and x is not None else "" for x in tabela["referência"]], textposition="outside",
                hovertemplate="%{y}: %{x:.1f}% do PIB<br>%{customdata}<extra></extra>")
    v.estilo(fig, altura=340)
    fig.update_xaxes(showticklabels=False, range=[0, 19.5])
    fig.update_yaxes(autorange="reversed", zeroline=False)
    v.mostra(fig, tabela, "gasto_por_funcao")
    v.leitura(
        "O governo geral (União, estados e municípios) gastou **45,8% do PIB** em 2024. A **proteção social** "
        "(Previdência, assistência) é a maior função, acima da média das economias avançadas; a **defesa**, "
        "1,1% do PIB, fica abaixo da metade da média mundial."
    )
    v.nota("COFOG do Tesouro (governo geral, 2023–2024) e SIPRI para defesa. O resultado primário acima cobre só o "
           "governo central.")

    # ------------------------------------------------------------ Orçamento e programas
    st.markdown("### Orçamento federal 2025 e programas sociais (R$ bilhões)")
    prog = d.filtra_tipos(d.tabela("defesa_e_programas_sociais"), tipos)
    col1, col2 = st.columns(2)
    with col1:
        loa = prog[prog["item"].str.contains("LOA")].sort_values("valor")
        fig = go.Figure(go.Bar(
            y=loa["item"].str.replace(" (LOA)", "", regex=False), x=loa["valor"], orientation="h",
            marker_color=c["serie"][0], text=[v.br(x, 0) for x in loa["valor"]], textposition="outside",
            hovertemplate="%{y}: R$ %{x:,.1f} bi<extra>LOA 2025</extra>",
        ))
        v.estilo(fig, altura=260, titulo="Lei Orçamentária 2025", legenda=False)
        fig.update_xaxes(showticklabels=False, range=[0, loa["valor"].max() * 1.2])
        fig.update_yaxes(zeroline=False)
        v.mostra(fig, loa, "loa_2025")
    with col2:
        bf = prog[prog["item"].str.startswith(("Bolsa Família", "Auxílio")) & (prog["unidade"] == "R$ bilhões")]
        bf = bf[~bf["item"].str.contains("LOA")].sort_values("ano")
        bf = d.filtra_periodo(bf, inicio, fim)
        if not bf.empty:
            fig = go.Figure(go.Bar(
                x=bf["ano"].astype(str), y=bf["valor"], marker_color=c["brasil"],
                marker_opacity=v.opacidades(bf["tipo"]), marker_pattern=v.padrao_barra(bf["tipo"]),
                text=[v.br(x, 0) for x in bf["valor"]], textposition="outside", customdata=bf["item"],
                hovertemplate="%{x}: R$ %{y:.1f} bi<br>%{customdata}<extra></extra>",
            ))
            v.estilo(fig, altura=260, titulo="Bolsa Família / Auxílio Brasil", legenda=False)
            fig.update_xaxes(type="category")
            fig.update_yaxes(showticklabels=False, range=[0, bf["valor"].max() * 1.2])
            v.mostra(fig, bf, "bolsa_familia")
    v.nota("Valores nominais, sem correção pela inflação. 2020: parte do público migrou para o Auxílio Emergencial "
           "(fora desta conta). 2022: Auxílio Brasil, valor aproximado (barra hachurada).")
