"""Aba Mundo: o Brasil comparado a outros países com dados abertos do Banco Mundial."""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from painel import banco_mundial as bm
from painel import dados as d
from painel import visual as v

PADRAO = ["Argentina", "Chile", "México", "China", "Estados Unidos"]
MEDIAS = ["Mundo", "América Latina e Caribe", "Membros da OCDE"]


@st.cache_data(ttl=24 * 3600, show_spinner="Buscando dados do Banco Mundial…")
def carrega() -> tuple[pd.DataFrame, str, list[str]]:
    """Retrato salvo, se houver; senão, a API ao vivo (guardada em cache por 24 horas)."""
    salvo = bm.retrato_salvo()
    if salvo is not None and not salvo.empty:
        return salvo, "retrato salvo em data/banco_mundial.csv", []
    tabela, falhas = bm.baixa_tudo(date.today().year)
    if tabela.empty:  # erro não entra no cache: a próxima visita tenta de novo
        raise RuntimeError("API do Banco Mundial sem resposta")
    return tabela, "API do Banco Mundial, consulta ao vivo", falhas


def comparacoes_do_pacote() -> None:
    """Cartões com as comparações internacionais que já vêm no pacote de dados."""
    paises = d.tabela("carga_tributaria_paises").rename(columns={"carga_pct_pib": "valor"})
    func = d.tabela("despesas_por_funcao")
    edu = d.tabela("educacao")
    fp = lambda nome, ano=None: float(func[(func["funcao"] == nome) & ((func["ano"] == ano) if ano else True)]["pct_pib"].iloc[0])  # noqa: E731
    v.kpis([
        {"rotulo": "Carga tributária 2024", "valor": v.br(d.valor(paises, pais="Brasil"), 1), "unidade": "% PIB",
         "detalhe": f"OCDE {v.br(d.valor(paises, pais='Média OCDE'), 1)}% · América Latina "
                    f"{v.br(d.valor(paises, pais='Média América Latina e Caribe'), 1)}%", "destaque": True},
        {"rotulo": "Proteção social 2023", "valor": v.br(fp("Proteção social", 2023), 1), "unidade": "% PIB",
         "detalhe": f"economias avançadas: {v.br(fp('Proteção social – média economias avançadas'), 1)}% (2022)"},
        {"rotulo": "Defesa 2025 (SIPRI)", "valor": v.br(fp("Defesa (SIPRI)", 2025), 1), "unidade": "% PIB",
         "detalhe": f"média mundial: {v.br(fp('Defesa – média mundial (SIPRI)'), 1)}%"},
        {"rotulo": "Pisa 2022: matemática", "valor": v.br(d.valor(edu, indicador="Pisa matemática"), 0),
         "unidade": "pontos", "detalhe": "média da OCDE: 472"},
        {"rotulo": "IDH 2023", "valor": "0,786", "detalhe": "84ª posição entre 193 países (PNUD)"},
    ])


def mostra(inicio: int, fim: int, tipos: list[str]) -> None:
    c = v.cores()
    st.markdown("### Brasil no mundo: o que o pacote de dados já compara")
    comparacoes_do_pacote()

    st.markdown("### Séries do Banco Mundial")
    v.leitura(
        "Indicadores do **World Development Indicators**, base aberta do Banco Mundial, para o Brasil e "
        "países de referência. Escolha o indicador e até cinco países para comparar; o Brasil aparece sempre "
        "em laranja."
    )
    try:
        wb, origem, falhas = carrega()
    except Exception as erro:  # rede fora do ar, por exemplo
        wb, origem, falhas = pd.DataFrame(), str(erro), list(bm.INDICADORES)
    if wb.empty:
        st.warning(
            "Não foi possível obter os dados do Banco Mundial agora (sem acesso à internet ou API fora do ar). "
            "Rode `python scripts/atualizar_banco_mundial.py` com internet para salvar um retrato em "
            "`data/banco_mundial.csv`; o painel passa a usá-lo."
        )
        return

    disponiveis = [k for k in bm.INDICADORES if k in set(wb["indicador"])]
    col1, col2 = st.columns([2, 3])
    with col1:
        codigo = st.selectbox("Indicador", disponiveis, format_func=lambda k: bm.INDICADORES[k][0], key="wb_indicador")
    nome, unidade, casas, descricao = bm.INDICADORES[codigo]
    nomes = [bm.PAISES[k][0] for k in bm.PAISES if k != "BRA" and bm.PAISES[k][1] != "Média"]
    with col2:
        escolhidos = st.multiselect("Comparar com (até 5)", nomes, default=PADRAO, max_selections=5, key="wb_paises")
    com_medias = st.toggle("Mostrar médias (Mundo, América Latina e Caribe, OCDE) em cinza", value=True, key="wb_medias")

    serie = wb[(wb["indicador"] == codigo) & wb["ano"].between(inicio, fim)]
    if serie.empty:
        st.info("Sem dados desse indicador no período escolhido.")
        return

    fig = go.Figure()
    tracejados = ["dot", "dash", "longdash"]
    if com_medias:
        for i, m in enumerate(MEDIAS):
            s = serie[serie["pais"] == m].sort_values("ano")
            if s.empty:
                continue
            fig.add_scatter(x=s["ano"], y=s["valor"], name=m, mode="lines",
                            line=dict(color=c["neutro"], width=1.5, dash=tracejados[i]),
                            hovertemplate=f"%{{x}}: %{{y:,.{casas}f}}<extra>{m}</extra>")
    for i, p in enumerate(escolhidos):  # a cor segue o país pela ordem de escolha
        s = serie[serie["pais"] == p].sort_values("ano")
        if s.empty:
            continue
        fig.add_scatter(x=s["ano"], y=s["valor"], name=p, mode="lines",
                        line=dict(color=c["serie"][i], width=2),
                        hovertemplate=f"%{{x}}: %{{y:,.{casas}f}}<extra>{p}</extra>")
    s = serie[serie["pais"] == "Brasil"].sort_values("ano")
    if not s.empty:
        fig.add_scatter(x=s["ano"], y=s["valor"], name="Brasil", mode="lines+markers",
                        line=dict(color=c["brasil"], width=3.5), marker=dict(size=5),
                        hovertemplate=f"%{{x}}: %{{y:,.{casas}f}}<extra>Brasil</extra>")
        ult = s.iloc[-1]
        fig.add_annotation(x=ult["ano"], y=ult["valor"], text=f"<b>Brasil {v.br(ult['valor'], casas)}</b>",
                           showarrow=False, xanchor="left", xshift=6, font=dict(color=c["brasil"]))
    v.estilo(fig, altura=420, titulo=f"{nome} ({unidade})")
    fig.update_layout(hovermode="x unified", margin=dict(t=48, r=90),
                      legend=dict(orientation="h", y=-0.1, yanchor="top", x=0, xanchor="left"))
    v.mostra(fig, serie.pivot_table(index="ano", columns="pais", values="valor").reset_index().round(casas + 1),
             f"banco_mundial_{codigo}")
    v.nota(f"{descricao} Fonte: Banco Mundial, indicador {codigo} ({origem}).")

    # ------------------------------------------------------------ Ranking no ano mais recente
    recente = serie.sort_values("ano").groupby("pais").tail(1)
    recente = recente[recente["ano"] >= recente["ano"].max() - 3].sort_values("valor")
    if len(recente) > 2:
        st.markdown(f"### {nome}: último dado de cada país")
        rotulos = [f"{p} ({a})" if a != recente["ano"].max() else p for p, a in zip(recente["pais"], recente["ano"])]
        # Cada país mantém a cor do gráfico de linhas; os demais ficam em cinza.
        cor_pais = {p: c["serie"][i] for i, p in enumerate(escolhidos)}
        cor = [c["brasil"] if p == "Brasil" else cor_pais.get(p, c["neutro_claro"] if g == "Média" else c["neutro"])
               for p, g in zip(recente["pais"], recente["grupo"])]
        fig = go.Figure(go.Bar(
            y=rotulos, x=recente["valor"], orientation="h", marker_color=cor,
            marker_pattern=dict(shape=["/" if g == "Média" else "" for g in recente["grupo"]], solidity=0.3, size=6),
            text=[v.br(x, casas) for x in recente["valor"]], textposition="outside",
            hovertemplate=f"%{{y}}: %{{x:,.{casas}f}}<extra></extra>",
        ))
        v.estilo(fig, altura=max(320, 24 * len(recente) + 40), legenda=False)
        menor = min(0, recente["valor"].min() * 1.15)
        fig.update_xaxes(showticklabels=False, range=[menor, recente["valor"].max() * 1.15])
        fig.update_yaxes(zeroline=False)
        v.mostra(fig, recente[["pais", "grupo", "ano", "valor"]], f"ranking_{codigo}")
        so_paises = recente[recente["grupo"] != "Média"].sort_values("valor", ascending=False).reset_index(drop=True)
        if "Brasil" in set(so_paises["pais"]):
            pos = int(so_paises.index[so_paises["pais"] == "Brasil"][0]) + 1
            v.frase(f"Brasil: {pos}º maior valor entre {len(so_paises)} países desta lista "
                    f"({v.br(float(so_paises.loc[pos - 1, 'valor']), casas)} {unidade}, {int(so_paises.loc[pos - 1, 'ano'])}).")
    if falhas:
        v.nota("Indicadores que não responderam nesta consulta: " + ", ".join(falhas) + ".")
