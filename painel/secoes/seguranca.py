"""Aba Segurança pública: Brasil e comparação entre os estados."""

from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from painel import dados as d
from painel import visual as v

# chave -> (nome, base da taxa, descrição curta)
INDICADORES = {
    "mvi": ("Mortes violentas intencionais", "hab",
            "Homicídio doloso, latrocínio, lesão corporal seguida de morte e mortes por intervenção policial."),
    "homicidio_doloso": ("Homicídio doloso (vítimas)", "hab", "Vítimas de homicídio com intenção de matar."),
    "latrocinio": ("Latrocínio", "hab", "Roubo seguido de morte."),
    "feminicidio": ("Feminicídio", "hab", "Assassinato de mulher por razões de gênero (tipificado em 2015)."),
    "estupro": ("Estupro", "hab", "Registros de estupro, inclusive de vulnerável. Há forte subnotificação."),
    "roubo_veiculo": ("Roubo de veículos", "veic", "Subtração com violência ou ameaça."),
    "furto_veiculo": ("Furto de veículos", "veic", "Subtração sem violência."),
    "roubo_carga": ("Roubo de carga", "hab", "Ocorrências de roubo de carga."),
    "morte_intervencao_policial": ("Mortes por intervenção policial", "hab",
                                   "Pessoas mortas por policiais civis e militares, em serviço ou de folga."),
    "policiais_mortos": ("Policiais mortos", "abs", "Policiais civis e militares mortos em confronto ou fora de serviço."),
    "armas_apreendidas": ("Armas de fogo apreendidas", "hab", "Armas apreendidas pelas polícias."),
    "desaparecidos": ("Pessoas desaparecidas", "hab", "Registros de desaparecimento."),
    "suicidio": ("Suicídios", "hab", "Registros policiais de suicídio."),
    "populacao_prisional": ("População prisional", "hab", "Pessoas no sistema penitenciário."),
    "despesa_seguranca": ("Gasto com segurança pública", "rs", "Despesa empenhada pelo estado, em reais correntes."),
}
UNIDADES = {
    "hab": "por 100 mil habitantes",
    "veic": "por 10 mil veículos",
    "abs": "total",
    "rs": "R$ por habitante (valores correntes)",
}
REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]


@st.cache_data
def mapa_uf() -> dict:
    return json.loads((d.PASTA_DADOS / "geo" / "uf.geojson").read_text())


def taxa(tabela: pd.DataFrame, chave: str) -> pd.Series:
    base = INDICADORES[chave][1]
    if base == "hab":
        return tabela[chave] / tabela["populacao"] * 1e5
    if base == "veic":
        return tabela[chave] / tabela["frota"] * 1e4
    if base == "rs":
        return tabela[chave] / tabela["populacao"]
    return tabela[chave]


def brasil(tabela: pd.DataFrame, chave: str) -> pd.DataFrame:
    """Valor nacional por ano, só quando todos os 27 estados informaram."""
    completos = tabela.dropna(subset=[chave]).groupby("ano").filter(lambda g: len(g) == 27)
    soma = completos.groupby("ano")[[chave, "populacao", "frota"]].sum().reset_index()
    soma["valor"] = taxa(soma, chave)
    return soma


def mostra(inicio: int, fim: int, tipos: list[str]) -> None:
    c = v.cores()
    uf = d.tabela("seguranca_uf")
    recente = d.tabela("seguranca_brasil_recente")

    def rv(indicador, ano=2025):
        return d.valor(recente, indicador=indicador, ano=ano)

    st.markdown("### Brasil em 2025")
    v.kpis([
        {"rotulo": "Mortes violentas intencionais", "valor": v.br(rv("Mortes violentas intencionais"), 0),
         "detalhe": f"{v.br(rv('Taxa de mortes violentas intencionais'), 1)} por 100 mil hab.: a menor taxa desde 2012",
         "destaque": True},
        {"rotulo": "Feminicídios", "valor": v.br(rv("Feminicídios"), 0),
         "detalhe": f"alta de {v.br(rv('Variação dos feminicídios'), 1)}% sobre 2024"},
        {"rotulo": "Mortes por intervenção policial", "valor": v.br(rv("Mortes decorrentes de intervenção policial"), 0),
         "detalhe": f"alta de {v.br(rv('Variação das mortes por intervenção policial'), 1)}% sobre 2024"},
        {"rotulo": "Estelionatos registrados", "valor": v.br(rv("Estelionatos registrados") / 1e6, 2), "unidade": "milhões",
         "detalhe": "o crime patrimonial mais registrado"},
    ])

    # ------------------------------------------------------------ Série nacional
    serie = brasil(uf, "mvi")[["ano", "mvi", "valor"]].rename(columns={"mvi": "vitimas", "valor": "taxa"})
    serie["tipo"] = "calculo"
    rec = recente[recente["indicador"].str.contains("ortes violentas")].pivot_table(
        index="ano", columns="indicador", values="valor").reset_index()
    rec = rec.rename(columns={"Mortes violentas intencionais": "vitimas", "Taxa de mortes violentas intencionais": "taxa"})
    serie = pd.concat([serie, rec.assign(tipo="oficial")], ignore_index=True)
    serie = d.filtra_tipos(d.filtra_periodo(serie, inicio, fim), tipos)
    if not serie.empty:
        st.markdown("### Mortes violentas intencionais no Brasil")
        fig = go.Figure(go.Scatter(
            x=serie["ano"], y=serie["taxa"], mode="lines+markers", line=dict(color=c["brasil"], width=3),
            marker=dict(size=9, color=c["brasil"], symbol=[v.simbolo(t) for t in serie["tipo"]], line=dict(width=2)),
            customdata=serie["vitimas"],
            hovertemplate="%{x}: %{y:.1f} por 100 mil<br>%{customdata:,.0f} vítimas<extra></extra>",
        ))
        pico = serie.loc[serie["taxa"].idxmax()]
        fig.add_annotation(x=pico["ano"], y=pico["taxa"], text=f"pico: {v.br(pico['taxa'], 1)}", showarrow=False,
                           yshift=16, font=dict(size=11))
        ult = serie.iloc[-1]
        fig.add_annotation(x=ult["ano"], y=ult["taxa"], text=f"{v.br(ult['taxa'], 1)}", showarrow=False, yshift=16,
                           font=dict(size=11, color=c["brasil"]))
        v.estilo(fig, altura=320, titulo="Taxa por 100 mil habitantes", legenda=False)
        fig.update_yaxes(rangemode="tozero")
        v.mostra(fig, serie, "seguranca_mvi_brasil")
        v.leitura(
            "A taxa chegou ao pico em **2017**, com mais de 64 mil mortes, e caiu desde então. Em 2025 ficou abaixo de "
            "20 por 100 mil pela primeira vez na série. Ainda assim, é o triplo da média mundial de homicídios (cerca de 6 "
            "por 100 mil, segundo o UNODC)."
        )
        v.nota("2011–2021: soma dos 27 estados na base do Anuário (Base dos Dados) dividida pela população do IBGE "
               "(cálculo próprio, marcador vazado). 2022–2025: valores publicados nos Anuários de 2024 e 2026. O Fórum "
               "revisa anos anteriores a cada edição; por isso 2021 aparece aqui com 47,5 mil mortes, e não com os "
               "48,4 mil da edição revisada.")

    mostra_estados(uf, inicio, fim)
    mostra_2025()


def mostra_estados(uf: pd.DataFrame, inicio: int, fim: int) -> None:
    c = v.cores()
    st.markdown("### Comparação entre os estados")
    v.leitura("Escolha o indicador e o ano. As taxas levam em conta o tamanho de cada estado: por habitante ou, "
              "para veículos, pelo tamanho da frota.")
    col1, col2 = st.columns([3, 2])
    with col1:
        chave = st.selectbox("Indicador", list(INDICADORES), format_func=lambda k: INDICADORES[k][0], key="seg_ind")
    nome, base, descricao = INDICADORES[chave]
    unidade = UNIDADES[base]
    dados_ind = uf.dropna(subset=[chave]).copy()
    dados_ind = dados_ind[dados_ind["ano"].between(inicio, fim)]
    if dados_ind.empty:
        st.info("Sem dados desse indicador no período escolhido.")
        return
    dados_ind["valor"] = taxa(dados_ind, chave)
    dados_ind = dados_ind.dropna(subset=["valor"])
    anos = sorted(dados_ind["ano"].unique())
    with col2:
        ano = st.select_slider("Ano", options=anos, value=anos[-1], key="seg_ano") if len(anos) > 1 else anos[0]
    no_ano = dados_ind[dados_ind["ano"] == ano].sort_values("valor")
    nacional = brasil(uf, chave)
    valor_br = nacional.loc[nacional["ano"] == ano, "valor"]
    valor_br = float(valor_br.iloc[0]) if not valor_br.empty and base != "abs" else None
    casas = 0 if base in ("abs", "rs") else 1

    col1, col2 = st.columns([1, 1])
    with col1:
        fig = go.Figure(go.Choropleth(
            geojson=mapa_uf(), featureidkey="id", locations=no_ano["sigla_uf"], z=no_ano["valor"],
            colorscale=[[0, "#deebf7"], [1, "#08306b"]] if v.modo() == "light" else [[0, "#1d3a5c"], [1, "#9ecae1"]],
            marker_line_color=c["fundo"], marker_line_width=0.8,
            customdata=no_ano[["uf"]], colorbar=dict(title=None, thickness=10, len=0.6),
            hovertemplate="%{customdata[0]}: %{z:,." + str(casas) + "f}<extra></extra>",
        ))
        fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
        v.estilo(fig, altura=420, titulo=f"{nome}, {ano}", legenda=False)
        fig.update_layout(margin=dict(l=0, r=0, t=48, b=0), geo=dict(bgcolor="rgba(0,0,0,0)"))
        v.mostra(fig)
    with col2:
        cor_regiao = {r: (c["serie"] + [c["neutro"]])[i] for i, r in enumerate(REGIOES)}
        fig = go.Figure()
        for regiao in REGIOES:
            g = no_ano[no_ano["regiao"] == regiao]
            fig.add_bar(y=g["sigla_uf"], x=g["valor"], orientation="h", name=regiao, marker_color=cor_regiao[regiao],
                        customdata=g[["uf"]], text=[v.br(x, casas) for x in g["valor"]], textposition="outside",
                        textfont=dict(size=10),
                        hovertemplate="%{customdata[0]}: %{x:,." + str(casas) + "f}<extra>" + regiao + "</extra>")
        if valor_br is not None:
            fig.add_vline(x=valor_br, line_color=c["brasil"], line_width=2, line_dash="dot")
            fig.add_annotation(x=valor_br, y=1, yref="paper", yanchor="bottom", showarrow=False,
                               text=f"Brasil: {v.br(valor_br, casas)}", font=dict(color=c["brasil"], size=11))
        v.estilo(fig, altura=620, eixo_y=None)
        fig.update_layout(barmode="overlay", bargap=0.2, legend=dict(y=-0.04, yanchor="top"), margin=dict(t=30))
        fig.update_yaxes(categoryorder="array", categoryarray=list(no_ano["sigla_uf"]), zeroline=False,
                         tickfont=dict(size=11))
        fig.update_xaxes(showticklabels=False, range=[0, no_ano["valor"].max() * 1.18])
        v.mostra(fig, no_ano[["sigla_uf", "uf", "regiao", chave, "populacao", "frota", "valor"]].rename(
            columns={"valor": f"taxa ({unidade})"}), f"seguranca_{chave}_{ano}")

    if len(no_ano) >= 2:
        alto, baixo = no_ano.iloc[-1], no_ano.iloc[0]
        v.frase(f"{nome}, {ano} ({unidade}): maior em {alto['uf']} ({v.br(alto['valor'], casas)}), "
                f"menor em {baixo['uf']} ({v.br(baixo['valor'], casas)}).")
    if len(no_ano) < 27:
        faltam = sorted(set(uf["sigla_uf"]) - set(no_ano["sigla_uf"]))
        v.nota(f"Sem dado em {ano}: {', '.join(faltam)}.")

    # ------------------------------------------------------------ Evolução
    padrao = [s for s in ["SP", "RJ", "BA", "CE", "AP"] if s in set(dados_ind["sigla_uf"])][:5]
    escolhidos = st.multiselect("Evolução: compare até 5 estados com o Brasil", sorted(dados_ind["sigla_uf"].unique()),
                                default=padrao, max_selections=5, key="seg_ufs",
                                format_func=lambda s: f"{s} – {uf.loc[uf['sigla_uf'] == s, 'uf'].iloc[0]}")
    fig = go.Figure()
    for i, sigla in enumerate(escolhidos):
        g = dados_ind[dados_ind["sigla_uf"] == sigla].sort_values("ano")
        fig.add_scatter(x=g["ano"], y=g["valor"], name=sigla, mode="lines+markers", line=dict(color=c["serie"][i], width=2),
                        marker=dict(size=6), hovertemplate="%{x}: %{y:,." + str(casas) + "f}<extra>" + sigla + "</extra>")
    nac = nacional[nacional["ano"].between(inicio, fim)]
    if base != "abs" and not nac.empty:
        fig.add_scatter(x=nac["ano"], y=nac["valor"], name="Brasil", mode="lines+markers",
                        line=dict(color=c["brasil"], width=3.5), marker=dict(size=7),
                        hovertemplate="%{x}: %{y:,." + str(casas) + "f}<extra>Brasil</extra>")
    v.estilo(fig, altura=380, titulo=f"{nome} ({unidade})")
    fig.update_layout(hovermode="x unified", legend=dict(y=-0.12, yanchor="top"))
    fig.update_yaxes(rangemode="tozero")
    v.mostra(fig, dados_ind[dados_ind["sigla_uf"].isin(escolhidos)].pivot_table(
        index="ano", columns="sigla_uf", values="valor").reset_index().round(2), f"seguranca_{chave}_evolucao")
    v.nota(f"{descricao} Fonte: Anuário Brasileiro de Segurança Pública (FBSP), dados por UF de 2007 a 2021, via Base "
           "dos Dados; população do IBGE e frota da Senatran. Taxas: cálculo próprio. Os registros dependem da polícia "
           "de cada estado, e a qualidade varia; zeros que indicam falta de coleta foram tratados como lacuna.")


def mostra_2025() -> None:
    c = v.cores()
    st.markdown("### Mortes violentas por estado em 2025")
    uf2025 = d.tabela("seguranca_mvi_uf_2025").sort_values("taxa_mvi")
    nomes = d.tabela("seguranca_uf").drop_duplicates("sigla_uf").set_index("sigla_uf")["uf"]
    recente = d.tabela("seguranca_brasil_recente")
    taxa_br = d.valor(recente, indicador="Taxa de mortes violentas intencionais", ano=2025)
    fig = go.Figure(go.Bar(
        y=[nomes.get(s, s) for s in uf2025["sigla_uf"]], x=uf2025["taxa_mvi"], orientation="h",
        marker_color=[c["serie"][0] if x > taxa_br else c["neutro"] for x in uf2025["taxa_mvi"]],
        text=[v.br(x, 1) for x in uf2025["taxa_mvi"]], textposition="outside",
        hovertemplate="%{y}: %{x:.1f} por 100 mil<extra></extra>",
    ))
    fig.add_vline(x=taxa_br, line_color=c["brasil"], line_width=2, line_dash="dot")
    fig.add_annotation(x=taxa_br, y=1, yref="paper", yanchor="bottom", showarrow=False,
                       text=f"Brasil: {v.br(taxa_br, 1)}", font=dict(color=c["brasil"], size=11))
    v.estilo(fig, altura=max(320, 26 * len(uf2025) + 60), legenda=False)
    fig.update_xaxes(showticklabels=False, range=[0, uf2025["taxa_mvi"].max() * 1.15])
    fig.update_yaxes(zeroline=False)
    fig.update_layout(margin=dict(t=30))
    v.mostra(fig, uf2025, "seguranca_mvi_uf_2025")
    faltam = sorted(set(nomes.index) - set(uf2025["sigla_uf"]))
    v.leitura("Amapá, Bahia e Ceará têm as maiores taxas; Santa Catarina e São Paulo, as menores, abaixo de 8 por 100 "
              "mil. Em azul, os estados acima da média nacional.")
    v.nota("Taxa de mortes violentas intencionais por 100 mil habitantes, 20º Anuário Brasileiro de Segurança Pública "
           f"(jul/2026), conforme divulgado pelo Fórum e pela imprensa. Ainda sem valor conferido: {', '.join(faltam)}.")
