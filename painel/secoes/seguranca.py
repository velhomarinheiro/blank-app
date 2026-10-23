"""Aba Segurança pública: Brasil e comparação entre os estados.

Dados do 20º Anuário Brasileiro de Segurança Pública (FBSP, 2026), importados por scripts/importar_anuario.py,
e da base histórica do Anuário por UF (2007–2021, via Base dos Dados), por scripts/preparar_seguranca.py.
"""

from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from painel import dados as d
from painel import visual as v

# Base histórica 2007–2021: chave -> (nome, base da taxa, descrição curta)
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


@st.cache_data
def nomes_uf() -> pd.DataFrame:
    """sigla -> nome e região (da base histórica)."""
    return d.tabela("seguranca_uf").drop_duplicates("sigla_uf").set_index("sigla_uf")[["uf", "regiao"]]


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


def mapa_e_ranking(tabela: pd.DataFrame, valor_br: float | None, titulo: str, casas: int, chave_csv: str,
                   hover_extra: str = "") -> None:
    """Mapa coroplético e ranking por região, lado a lado. `tabela` tem sigla_uf, valor e (opcional) detalhe."""
    c = v.cores()
    info = nomes_uf()
    tabela = tabela.join(info, on="sigla_uf").sort_values("valor")
    detalhe = tabela["detalhe"] if "detalhe" in tabela else pd.Series("", index=tabela.index)
    col1, col2 = st.columns([1, 1])
    with col1:
        fig = go.Figure(go.Choropleth(
            geojson=mapa_uf(), featureidkey="id", locations=tabela["sigla_uf"], z=tabela["valor"],
            colorscale=[[0, "#deebf7"], [1, "#08306b"]] if v.modo() == "light" else [[0, "#1d3a5c"], [1, "#9ecae1"]],
            marker_line_color=c["fundo"], marker_line_width=0.8,
            customdata=pd.concat([tabela["uf"], detalhe], axis=1), colorbar=dict(title=None, thickness=10, len=0.6),
            hovertemplate="%{customdata[0]}: %{z:,." + str(casas) + "f}%{customdata[1]}<extra></extra>",
        ))
        fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
        v.estilo(fig, altura=440, titulo=titulo, legenda=False)
        fig.update_layout(margin=dict(l=0, r=0, t=48, b=0), geo=dict(bgcolor="rgba(0,0,0,0)"))
        v.mostra(fig)
    with col2:
        cor_regiao = {r: c["serie"][i] for i, r in enumerate(REGIOES)}
        fig = go.Figure()
        for regiao in REGIOES:
            g = tabela[tabela["regiao"] == regiao]
            fig.add_bar(y=g["sigla_uf"], x=g["valor"], orientation="h", name=regiao, marker_color=cor_regiao[regiao],
                        customdata=pd.concat([g["uf"], detalhe.loc[g.index]], axis=1),
                        text=[v.br(x, casas) for x in g["valor"]], textposition="outside", textfont=dict(size=10),
                        hovertemplate="%{customdata[0]}: %{x:,." + str(casas) + "f}%{customdata[1]}<extra>"
                                      + regiao + "</extra>")
        if valor_br is not None:
            fig.add_vline(x=valor_br, line_color=c["brasil"], line_width=2, line_dash="dot")
            fig.add_annotation(x=valor_br, y=1, yref="paper", yanchor="bottom", showarrow=False,
                               text=f"Brasil: {v.br(valor_br, casas)}", font=dict(color=c["brasil"], size=11))
        v.estilo(fig, altura=620)
        fig.update_layout(barmode="overlay", bargap=0.2, legend=dict(y=-0.04, yanchor="top"), margin=dict(t=30))
        fig.update_yaxes(categoryorder="array", categoryarray=list(tabela["sigla_uf"]), zeroline=False,
                         tickfont=dict(size=11))
        fig.update_xaxes(showticklabels=False, range=[0, tabela["valor"].max() * 1.18])
        v.mostra(fig, tabela.drop(columns=["detalhe"], errors="ignore"), chave_csv)
    if len(tabela) >= 2:
        alto, baixo = tabela.iloc[-1], tabela.iloc[0]
        v.frase(f"{titulo}: maior em {alto['uf']} ({v.br(alto['valor'], casas)}), "
                f"menor em {baixo['uf']} ({v.br(baixo['valor'], casas)}).")


def mostra(inicio: int, fim: int, tipos: list[str]) -> None:
    rec = d.tabela("seguranca_uf_recente")
    ultimo = int(rec["ano"].max())
    br = rec[(rec["sigla_uf"] == "BR")].pivot_table(index="indicador", columns="ano", values="valor")
    br_taxa = rec[(rec["sigla_uf"] == "BR")].pivot_table(index="indicador", columns="ano", values="taxa")

    def var(chave):
        # Pela taxa, como no Anuário: desconta o crescimento da população (ou da frota).
        return (br_taxa.loc[chave, ultimo] / br_taxa.loc[chave, ultimo - 1] - 1) * 100

    def cartao(chave, rotulo, destaque=False, milhoes=False):
        valor = br.loc[chave, ultimo]
        texto = v.br(valor / 1e6, 2) if milhoes else v.br(valor, 0)
        return {"rotulo": rotulo, "valor": texto, "unidade": "milhões" if milhoes else None,
                "detalhe": f"taxa {v.br(var(chave), 1, sinal=True)}% sobre {ultimo - 1}", "destaque": destaque}

    serie = d.tabela("seguranca_mvi_serie")
    taxa_br = serie[(serie["sigla_uf"] == "BR") & (serie["ano"] == ultimo)]["taxa"].iloc[0]
    st.markdown(f"### Brasil em {ultimo}")
    v.kpis([
        {**cartao("mvi", "Mortes violentas intencionais", destaque=True),
         "detalhe": f"{v.br(taxa_br, 1)} por 100 mil hab. ({v.br(var('mvi'), 1, sinal=True)}%), a menor taxa da série"},
        cartao("feminicidio", "Feminicídios"),
        cartao("morte_intervencao_policial", "Mortes por intervenção policial"),
        cartao("estupro", "Estupros (inclui vulnerável)"),
        {**cartao("roubo_celular", "Celulares roubados (registros)"), },
        cartao("estelionato", "Estelionatos", milhoes=True),
    ])

    mostra_serie_nacional(serie, inicio, fim)
    mostra_estados_recente(rec, ultimo)
    mostra_linha_do_tempo(inicio, fim)
    mostra_prisional(inicio, fim)
    mostra_historico(d.tabela("seguranca_uf"), inicio, fim)


def mostra_serie_nacional(serie: pd.DataFrame, inicio: int, fim: int) -> None:
    c = v.cores()
    st.markdown("### Mortes violentas intencionais no Brasil e nas regiões")
    s = serie[serie["nivel"].isin(["brasil", "regiao"]) & serie["ano"].between(inicio, fim)]
    if s.empty:
        return
    fig = go.Figure()
    for i, regiao in enumerate(REGIOES):
        g = s[s["sigla_uf"] == regiao].sort_values("ano")
        fig.add_scatter(x=g["ano"], y=g["taxa"], name=regiao, mode="lines", line=dict(color=c["serie"][i], width=2),
                        customdata=g["mvi"],
                        hovertemplate="%{x}: %{y:.1f} por 100 mil (%{customdata:,.0f} vítimas)<extra>" + regiao + "</extra>")
    g = s[s["sigla_uf"] == "BR"].sort_values("ano")
    fig.add_scatter(x=g["ano"], y=g["taxa"], name="Brasil", mode="lines+markers", line=dict(color=c["brasil"], width=3.5),
                    marker=dict(size=7), customdata=g["mvi"],
                    hovertemplate="%{x}: %{y:.1f} por 100 mil (%{customdata:,.0f} vítimas)<extra>Brasil</extra>")
    if not g.empty:
        pico = g.loc[g["taxa"].idxmax()]
        ult = g.iloc[-1]
        fig.add_annotation(x=pico["ano"], y=pico["taxa"], text=f"pico: {v.br(pico['taxa'], 1)}", showarrow=False,
                           yshift=14, font=dict(size=11, color=c["brasil"]))
        fig.add_annotation(x=ult["ano"], y=ult["taxa"], text=v.br(ult["taxa"], 1), showarrow=False, yshift=-14,
                           font=dict(size=11, color=c["brasil"]))
    v.estilo(fig, altura=380, titulo="Taxa por 100 mil habitantes")
    fig.update_layout(hovermode="x unified", legend=dict(y=-0.12, yanchor="top"))
    fig.update_yaxes(rangemode="tozero")
    v.mostra(fig, s.pivot_table(index="ano", columns="sigla_uf", values="taxa").reset_index().round(2),
             "seguranca_mvi_regioes")
    v.leitura(
        "A taxa nacional chegou ao pico em **2017**, com 64 mil mortes, e caiu desde então: em 2025 ficou abaixo de 20 "
        "por 100 mil pela primeira vez na série. O **Nordeste** e o **Norte** seguem bem acima da média; o **Sudeste** "
        "e o **Sul**, abaixo. Mesmo assim, o Brasil tem cerca de três vezes a taxa mundial de homicídios (perto de 6 "
        "por 100 mil, segundo o UNODC)."
    )
    v.nota("Mortes violentas intencionais: homicídio doloso, latrocínio, lesão corporal seguida de morte e mortes por "
           "intervenção policial. Fonte: 20º Anuário Brasileiro de Segurança Pública (FBSP, 2026), Tabela 02, com os "
           "anos anteriores revisados.")


def mostra_estados_recente(rec: pd.DataFrame, ultimo: int) -> None:
    st.markdown(f"### Os estados em {ultimo}")
    v.leitura("Escolha o indicador. As taxas são as publicadas pelo Fórum: por 100 mil habitantes, por 100 mil "
              "mulheres (feminicídio) ou por 100 mil veículos (roubo e furto de veículos).")
    rotulos = rec.drop_duplicates("indicador").set_index("indicador")["rotulo"]
    chave = st.selectbox("Indicador", list(rotulos.index), format_func=rotulos.get, key="seg_rec_ind")
    dados = rec[rec["indicador"] == chave]
    base = dados["base_taxa"].iloc[0]
    atual = dados[dados["ano"] == ultimo].set_index("sigla_uf")
    anterior = dados[dados["ano"] == ultimo - 1].set_index("sigla_uf")
    tabela = pd.DataFrame({"valor": atual["taxa"], "registros": atual["valor"],
                           "variacao": (atual["taxa"] / anterior["taxa"] - 1) * 100}).reset_index()
    valor_br = float(tabela.loc[tabela["sigla_uf"] == "BR", "valor"].iloc[0])
    tabela = tabela[tabela["sigla_uf"] != "BR"].dropna(subset=["valor"])
    tabela["detalhe"] = [f" ({v.br(r, 0)} registros; {v.br(x, 1, sinal=True)}% sobre {ultimo - 1})"
                         if pd.notna(x) else f" ({v.br(r, 0)} registros)"
                         for r, x in zip(tabela["registros"], tabela["variacao"])]
    casas = 0 if tabela["valor"].max() >= 100 else 1
    mapa_e_ranking(tabela, valor_br, f"{rotulos[chave]}, {ultimo} ({base})", casas, f"seguranca_{chave}_{ultimo}")
    subiu = tabela[tabela["variacao"] > 0].sort_values("variacao", ascending=False)
    if not subiu.empty:
        info = nomes_uf()
        nomes = ", ".join(f"{info.loc[s, 'uf']} ({v.br(x, 1, sinal=True)}%)" for s, x in
                          zip(subiu["sigla_uf"].head(5), subiu["variacao"].head(5)))
        v.nota(f"{len(subiu)} estado(s) com alta da taxa sobre {ultimo - 1}. Maiores altas: {nomes}. Fonte: "
               f"{dados['fonte'].iloc[0]}.")


UNIDADES_SERIE = {
    "hab": "por 100 mil habitantes",
    "veic": "por 100 mil veículos",
    "pct": "% dos homicídios de mulheres",
    "rs": "R$ por habitante (valores de 2025)",
}
NOTAS_SERIE = {
    "apreensao_drogas": "Os estados contam apreensões de formas diferentes; compare a tendência de cada um, não os níveis.",
    "armas_registradas": "Registros ativos no Sinarm (Polícia Federal), de cidadãos, empresas e órgãos públicos.",
    "proporcao_feminicidio": "Parte da alta reflete a melhora no registro: a lei do feminicídio é de 2015.",
    "despesa_seguranca": "Despesa dos estados com a função Segurança Pública, em reais de 2025.",
    "posse_uso_drogas": "Registros policiais; dependem das prioridades e da forma de registro de cada polícia.",
    "trafico_drogas": "Registros policiais; dependem das prioridades e da forma de registro de cada polícia.",
}


def mostra_linha_do_tempo(inicio: int, fim: int) -> None:
    """Linha do tempo de qualquer indicador, para o Brasil e até 5 estados."""
    c = v.cores()
    st.markdown("### Linha do tempo por indicador")
    series = d.tabela("seguranca_series")
    series = series[series["ano"].between(inicio, fim)]
    if series.empty:
        return
    rotulos = series.drop_duplicates("indicador").set_index("indicador")["rotulo"]
    ordem = ["mvi"] + sorted([k for k in rotulos.index if k != "mvi"], key=lambda k: rotulos[k])
    info = nomes_uf()
    col1, col2 = st.columns([3, 2])
    with col1:
        chave = st.selectbox("Indicador", ordem, format_func=rotulos.get, key="seg_linha_ind")
    dados = series[series["indicador"] == chave]
    base = dados["base"].iloc[0]
    with col2:
        opcoes = ["Taxa", "Números absolutos"] if base != "pct" else ["Taxa"]
        medida = st.radio("Medida", opcoes, horizontal=True, key="seg_linha_medida")
    coluna = "taxa" if medida == "Taxa" else "valor"
    unidade = UNIDADES_SERIE[base] if coluna == "taxa" else ("R$ (valores de 2025)" if base == "rs" else "registros")
    padrao = [x for x in ["SP", "RJ", "BA", "CE", "AP"] if x in set(dados["sigla_uf"])]
    escolhidos = st.multiselect("Compare até 5 estados com o Brasil", sorted(set(dados["sigla_uf"]) - {"BR"}),
                                default=padrao, max_selections=5, key="seg_ufs_mvi",
                                format_func=lambda x: f"{x} – {info.loc[x, 'uf']}")
    anos = pd.DataFrame({"ano": range(int(dados["ano"].min()), int(dados["ano"].max()) + 1)})
    grande = dados[coluna].abs().max() >= 1000
    casas = 0 if grande or coluna == "valor" else 1
    fig = go.Figure()
    linhas = [(s, c["serie"][i], 2, f"{s}") for i, s in enumerate(escolhidos)] + [("BR", c["brasil"], 3.5, "Brasil")]
    for sigla, cor, largura, nome in linhas:
        g = anos.merge(dados[dados["sigla_uf"] == sigla], on="ano", how="left")  # anos sem dado ficam como lacuna
        if g[coluna].isna().all():
            continue
        fig.add_scatter(x=g["ano"], y=g[coluna], name=nome, mode="lines+markers", connectgaps=False,
                        line=dict(color=cor, width=largura), marker=dict(size=7 if sigla == "BR" else 6),
                        hovertemplate="%{x}: %{y:,." + str(casas) + "f}<extra>" + nome + "</extra>")
    v.estilo(fig, altura=400, titulo=f"{rotulos[chave]} ({unidade})")
    fig.update_layout(hovermode="x unified", legend=dict(y=-0.12, yanchor="top"))
    fig.update_yaxes(rangemode="tozero")
    if grande:
        fig.update_yaxes(tickformat=",.0f")
    fig.update_xaxes(dtick=2 if len(anos) > 10 else 1)
    tabela = dados[dados["sigla_uf"].isin(escolhidos + ["BR"])].pivot_table(
        index="ano", columns="sigla_uf", values=coluna).reset_index().round(2)
    v.mostra(fig, tabela, f"seguranca_linha_{chave}")

    # Quem mais mudou: médias dos três primeiros e dos três últimos anos com dado (um ano atípico não distorce).
    estados = dados[(dados["sigla_uf"] != "BR")].dropna(subset=[coluna])
    a, b = int(estados["ano"].min()), int(estados["ano"].max())
    if b - a >= 5:
        ini = estados[estados["ano"].between(a, a + 2)].groupby("sigla_uf")[coluna].mean()
        fimv = estados[estados["ano"].between(b - 2, b)].groupby("sigla_uf")[coluna].mean()
        mudanca = ((fimv / ini - 1) * 100).replace([float("inf"), float("-inf")], float("nan")).dropna().sort_values()
        if len(mudanca) >= 3:
            def nome(i):
                return f"**{info.loc[mudanca.index[i], 'uf']}** ({v.br(mudanca.iloc[i], 0, sinal=True)}%)"
            v.leitura(f"Comparando a média de {a}–{a + 2} com a de {b - 2}–{b}: maiores quedas em {nome(0)} e "
                      f"{nome(1)}; maior alta em {nome(-1)}. Anos sem dado entram fora da média.")

    sem = sorted(set(range(int(dados["ano"].min()), int(dados["ano"].max()) + 1))
                 - set(dados.loc[dados["sigla_uf"] == "BR", "ano"]))
    fontes = " e ".join(sorted(dados["fonte"].unique()))
    partes = [NOTAS_SERIE.get(chave, "")]
    if sem:
        partes.append(f"Sem total nacional em {', '.join(map(str, sem))}: anos em que nem todos os estados "
                      "informaram ou que nenhuma das fontes cobre (lacunas não são preenchidas).")
    if coluna == "taxa" and base in ("hab", "rs"):
        partes.append("Taxas calculadas com a população do IBGE (até 2021) e a usada pelo Fórum (depois).")
    elif coluna == "taxa" and base == "veic":
        partes.append("Taxas por 100 mil veículos da frota registrada na Senatran.")
    partes.append(f"Fonte: {fontes}.")
    v.nota(" ".join(p for p in partes if p))


def mostra_prisional(inicio: int, fim: int) -> None:
    c = v.cores()
    p = d.filtra_periodo(d.tabela("seguranca_prisional"), inicio, fim)
    if p.empty:
        return
    st.markdown("### População prisional")
    fig = go.Figure(go.Bar(
        x=p["ano"], y=p["total"] / 1e3, marker_color=c["serie"][0],
        hovertemplate="%{x}: %{y:,.0f} mil pessoas<extra></extra>",
    ))
    ult = p.iloc[-1]
    fig.add_annotation(x=ult["ano"], y=ult["total"] / 1e3, text=f"{v.br(ult['total'] / 1e3, 0)} mil", showarrow=False,
                       yshift=12, font=dict(size=11))
    v.estilo(fig, altura=300, titulo="Pessoas privadas de liberdade (mil)", legenda=False)
    v.mostra(fig, p, "seguranca_populacao_prisional")
    primeiro = p.iloc[0]
    v.nota(f"De {int(primeiro['ano'])} a {int(ult['ano'])}, a população prisional passou de "
           f"{v.br(primeiro['total'] / 1e3, 0)} mil para {v.br(ult['total'] / 1e3, 0)} mil pessoas. Inclui o sistema "
           "penitenciário e presos sob custódia das polícias. Fonte: Sisdepen/MJSP, compilado pelo FBSP (Tabela 75).")


def mostra_historico(uf: pd.DataFrame, inicio: int, fim: int) -> None:
    """Base histórica por UF (2007–2021) para indicadores sem série recente."""
    c = v.cores()
    with st.expander("Série histórica de outros indicadores por estado (2007–2021)"):
        v.leitura("Base histórica do Anuário por UF, até 2021, com taxas calculadas a partir da população do IBGE e "
                  "da frota da Senatran.")
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
        no_ano = dados_ind[dados_ind["ano"] == ano][["sigla_uf", "valor"]]
        nacional = brasil(uf, chave)
        valor_br = nacional.loc[nacional["ano"] == ano, "valor"]
        valor_br = float(valor_br.iloc[0]) if not valor_br.empty and base != "abs" else None
        casas = 0 if base in ("abs", "rs") else 1
        mapa_e_ranking(no_ano, valor_br, f"{nome}, {ano} ({unidade})", casas, f"seguranca_hist_{chave}_{ano}")
        if len(no_ano) < 27:
            faltam = sorted(set(uf["sigla_uf"]) - set(no_ano["sigla_uf"]))
            v.nota(f"Sem dado em {ano}: {', '.join(faltam)}.")

        escolhidos = st.multiselect("Evolução: compare até 5 estados com o Brasil", sorted(dados_ind["sigla_uf"].unique()),
                                    default=[s for s in ["SP", "RJ", "BA", "CE", "AP"] if s in set(dados_ind["sigla_uf"])],
                                    max_selections=5, key="seg_ufs")
        fig = go.Figure()
        for i, sigla in enumerate(escolhidos):
            g = dados_ind[dados_ind["sigla_uf"] == sigla].sort_values("ano")
            fig.add_scatter(x=g["ano"], y=g["valor"], name=sigla, mode="lines+markers",
                            line=dict(color=c["serie"][i], width=2), marker=dict(size=6),
                            hovertemplate="%{x}: %{y:,." + str(casas) + "f}<extra>" + sigla + "</extra>")
        nac = nacional[nacional["ano"].between(inicio, fim)]
        if base != "abs" and not nac.empty:
            fig.add_scatter(x=nac["ano"], y=nac["valor"], name="Brasil", mode="lines+markers",
                            line=dict(color=c["brasil"], width=3.5), marker=dict(size=7),
                            hovertemplate="%{x}: %{y:,." + str(casas) + "f}<extra>Brasil</extra>")
        v.estilo(fig, altura=360, titulo=f"{nome} ({unidade})")
        fig.update_layout(hovermode="x unified", legend=dict(y=-0.12, yanchor="top"))
        fig.update_yaxes(rangemode="tozero")
        v.mostra(fig, dados_ind[dados_ind["sigla_uf"].isin(escolhidos)].pivot_table(
            index="ano", columns="sigla_uf", values="valor").reset_index().round(2), f"seguranca_hist_{chave}_evolucao")
        v.nota(f"{descricao} Fonte: Anuário Brasileiro de Segurança Pública (FBSP), dados por UF de 2007 a 2021, via "
               "Base dos Dados; população do IBGE e frota da Senatran. Taxas: cálculo próprio. Zeros que indicam falta "
               "de coleta foram tratados como lacuna.")
