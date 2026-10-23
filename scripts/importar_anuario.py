"""Importa a planilha do Anuário Brasileiro de Segurança Pública (FBSP) para os arquivos do painel.

    pip install openpyxl
    python scripts/importar_anuario.py caminho/anuario-2026.xlsx

Grava:
- data/dados/seguranca_mvi_serie.csv   Tabela 02: mortes violentas por UF e região, 2012–2025
- data/dados/seguranca_uf_recente.csv  Tabelas por UF dos dois últimos anos (vítimas/registros e taxas publicadas)
- data/dados/seguranca_prisional.csv   Tabela 75: população prisional, Brasil, 2000–2025
- data/dados/seguranca_series.csv      Linha do tempo de cada indicador por UF, juntando a base histórica
                                       (data/dados/seguranca_uf.csv, de scripts/preparar_seguranca.py) e o Anuário

As posições das colunas seguem o layout do 20º Anuário (2026). Se uma edição futura mudar o layout, o script
avisa qual tabela não bateu, em vez de gravar números trocados.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import openpyxl
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent / "data" / "dados"

UFS = {
    "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM", "Bahia": "BA", "Ceará": "CE",
    "Distrito Federal": "DF", "Espírito Santo": "ES", "Goiás": "GO", "Maranhão": "MA", "Mato Grosso": "MT",
    "Mato Grosso do Sul": "MS", "Minas Gerais": "MG", "Pará": "PA", "Paraíba": "PB", "Paraná": "PR",
    "Pernambuco": "PE", "Piauí": "PI", "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN",
    "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR", "Santa Catarina": "SC", "São Paulo": "SP",
    "Sergipe": "SE", "Tocantins": "TO", "Brasil": "BR",
    "Região Norte": "N", "Região Nordeste": "NE", "Região Centro-Oeste": "CO", "Região Sudeste": "SE_R",
    "Região Sul": "S",
}

REGIOES = {"N", "NE", "CO", "SE_R", "S"}

# chave -> (aba, coluna do número de 2024, coluna da taxa de 2024, rótulo, base da taxa)
# O valor de 2025 fica na coluna seguinte a cada uma. Colunas contadas a partir de 0 (a 0 é o nome da UF).
INDICADORES = {
    "mvi": ("T01", 11, 13, "Mortes violentas intencionais", "por 100 mil habitantes"),
    "homicidio_doloso": ("T03", 1, 3, "Homicídio doloso (vítimas)", "por 100 mil habitantes"),
    "latrocinio": ("T04", 1, 3, "Latrocínio (vítimas)", "por 100 mil habitantes"),
    "morte_intervencao_policial": ("T08", 9, 11, "Mortes por intervenção policial", "por 100 mil habitantes"),
    "feminicidio": ("T21", 6, 8, "Feminicídio", "por 100 mil mulheres"),
    "homicidio_mulheres": ("T21", 1, 3, "Homicídios de mulheres", "por 100 mil mulheres"),
    "tentativa_homicidio": ("T20", 1, 3, "Tentativa de homicídio", "por 100 mil habitantes"),
    "estupro": ("T29", 11, 13, "Estupro e estupro de vulnerável", "por 100 mil habitantes"),
    "roubo_celular": ("T12", 1, 3, "Roubo de celular", "por 100 mil habitantes"),
    "furto_celular": ("T12", 6, 8, "Furto de celular", "por 100 mil habitantes"),
    "roubo_veiculo": ("T11", 1, 3, "Roubo de veículos", "por 100 mil veículos"),
    "furto_veiculo": ("T11", 6, 8, "Furto de veículos", "por 100 mil veículos"),
    "roubo_transeunte": ("T14", 11, 13, "Roubo a transeunte", "por 100 mil habitantes"),
    "roubo_residencia": ("T14", 6, 8, "Roubo a residência", "por 100 mil habitantes"),
    "roubo_comercio": ("T14", 1, 3, "Roubo a estabelecimento comercial", "por 100 mil habitantes"),
    "roubo_carga": ("T15", 6, 8, "Roubo de carga", "por 100 mil habitantes"),
    "estelionato": ("T17", 1, 3, "Estelionato", "por 100 mil habitantes"),
    "desaparecidos": ("T10", 1, 3, "Pessoas desaparecidas", "por 100 mil habitantes"),
    "armas_apreendidas": ("T48", 1, 3, "Armas de fogo apreendidas (polícias estaduais)", "por 100 mil habitantes"),
    "populacao_prisional": ("T71", 5, 7, "Pessoas privadas de liberdade", "por 100 mil habitantes"),
}
# Texto que precisa aparecer no cabeçalho de cada aba (confere se a edição tem o mesmo layout).
CONFERE = {
    "T01": "Mortes violentas", "T02": "Mortes Violentas", "T03": "Homicídios dolosos", "T04": "Latrocínio",
    "T08": "intervenç", "T10": "desaparecidas", "T11": "veículo", "T12": "celular", "T14": "Roubo a",
    "T15": "carga", "T17": "Estelionato", "T20": "Tentativa", "T21": "eminicídio", "T29": "Estupro",
    "T48": "armas", "T71": "privadas de liberdade", "T75": "população prisional",
    "T51": "tráfico", "T52": "posse e uso", "T53": "apreensão", "T45": "arma de fogo", "T28": "feminicídio",
    "T56": "despesas",
}


def nome_uf(texto) -> str | None:
    """'Minas Gerais (6)' -> 'MG'; devolve None se a linha não for de UF, região ou Brasil."""
    if texto is None:
        return None
    limpo = re.sub(r"\s*\(\d+\)", "", str(texto)).strip()
    return UFS.get(limpo)


def numero(valor) -> float | None:
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    if texto == "-":          # fenômeno inexistente
        return 0.0
    if texto in ("...", "", "NT", "n/d"):
        return None
    try:
        return float(texto.replace(".", "").replace(",", ".")) if "," in texto else float(texto)
    except ValueError:
        return None


def linhas(planilha, aba: str) -> list[tuple]:
    ws = planilha[aba]
    todas = list(ws.iter_rows(values_only=True))
    cabecalho = " ".join(str(c) for r in todas[:8] for c in r if c)
    if CONFERE[aba].lower() not in cabecalho.lower():
        raise ValueError(f"A aba {aba} não parece ser a esperada ('{CONFERE[aba]}'). O layout mudou?")
    return todas


def anos_da_tabela(todas: list[tuple], coluna: int) -> tuple[int, int]:
    """Lê os anos no cabeçalho (ex.: '2024 (3)' e '2025')."""
    for r in todas[:10]:
        if len(r) > coluna + 1 and r[coluna] and re.match(r"^\d{4}", str(r[coluna])):
            return int(str(r[coluna])[:4]), int(str(r[coluna + 1])[:4])
    raise ValueError("Anos não encontrados no cabeçalho")


def recentes(planilha) -> pd.DataFrame:
    saida = []
    for chave, (aba, col_n, col_t, rotulo, base) in INDICADORES.items():
        todas = linhas(planilha, aba)
        ano_a, ano_b = anos_da_tabela(todas, col_n)
        for r in todas:
            sigla = nome_uf(r[0]) if r else None
            if sigla is None or sigla in REGIOES:
                continue
            for ano, desloc in ((ano_a, 0), (ano_b, 1)):
                saida.append({"indicador": chave, "rotulo": rotulo, "sigla_uf": sigla, "ano": ano,
                              "valor": numero(r[col_n + desloc]), "taxa": numero(r[col_t + desloc]), "base_taxa": base,
                              "fonte": f"FBSP, 20º Anuário, {aba.replace('T', 'Tabela ')}"})
    tabela = pd.DataFrame(saida)
    # Conferência: cada indicador precisa ter Brasil e as 27 UFs.
    contagem = tabela.groupby(["indicador", "ano"])["sigla_uf"].nunique()
    if (contagem != 28).any():
        raise ValueError(f"UFs faltando: {contagem[contagem != 28].to_dict()}")
    return tabela


def serie_mvi(planilha) -> pd.DataFrame:
    todas = linhas(planilha, "T02")
    anos = next(r for r in todas[:10] if r[1] and str(r[1]).startswith("20"))
    n_anos = sum(1 for c in anos[1:] if c and re.match(r"^\d{4}$", str(c))) // 2
    anos = [int(c) for c in anos[1:1 + n_anos]]
    saida = []
    for r in todas:
        sigla = nome_uf(r[0]) if r else None
        if sigla is None:
            continue
        for i, ano in enumerate(anos):
            nivel = "regiao" if sigla in REGIOES else ("brasil" if sigla == "BR" else "uf")
            saida.append({"sigla_uf": sigla, "nivel": nivel, "ano": ano,
                          "mvi": numero(r[1 + i]), "taxa": numero(r[1 + n_anos + i])})
    tabela = pd.DataFrame(saida)
    tabela["sigla_uf"] = tabela["sigla_uf"].replace({"SE_R": "Sudeste"}).replace(
        {"N": "Norte", "NE": "Nordeste", "CO": "Centro-Oeste", "S": "Sul"})
    return tabela


def prisional(planilha) -> pd.DataFrame:
    todas = linhas(planilha, "T75")
    anos = next(r for r in todas if r[1] and str(r[1]).startswith("20"))
    anos = [int(c) for c in anos[1:] if c and re.match(r"^\d{4}$", str(c))]
    rotulos = {"Presos no Sistem": "sistema_penitenciario", "Presos sob Custó": "custodia_policias",
               "Total de pessoas": "total"}
    saida = []
    for r in todas:
        chave = next((v for k, v in rotulos.items() if r[0] and str(r[0]).startswith(k)), None)
        if chave:
            for i, ano in enumerate(anos):
                saida.append({"ano": ano, "serie": chave, "pessoas": numero(r[1 + i])})
    return pd.DataFrame(saida).pivot_table(index="ano", columns="serie", values="pessoas").reset_index()


# ---------------------------------------------------------------- linha do tempo dos indicadores

# Séries de vários anos que vêm prontas no Anuário: chave -> (aba, rótulo, base da taxa)
SERIES_LONGAS = {
    "trafico_drogas": ("T51", "Tráfico de drogas (registros)", "hab"),
    "posse_uso_drogas": ("T52", "Posse e uso de drogas (registros)", "hab"),
    "apreensao_drogas": ("T53", "Apreensões de drogas (registros)", "hab"),
    "armas_registradas": ("T45", "Armas de fogo com registro ativo (Sinarm/PF)", "hab"),
    "proporcao_feminicidio": ("T28", "Feminicídios entre os homicídios de mulheres", "pct"),
    "despesa_seguranca": ("T56", "Gasto estadual com segurança pública (R$ de 2025)", "rs"),
}
# Indicadores montados com a base histórica por UF (2007–2021) e o Anuário 2026 (2024–2025):
# chave -> (rótulo, base da taxa). A chave é a mesma nas duas fontes.
COMBINADAS = {
    "homicidio_doloso": ("Homicídio doloso (vítimas)", "hab"),
    "latrocinio": ("Latrocínio (vítimas)", "hab"),
    "morte_intervencao_policial": ("Mortes por intervenção policial", "hab"),
    "feminicidio": ("Feminicídio", "hab"),
    "estupro": ("Estupro e estupro de vulnerável", "hab"),
    "roubo_veiculo": ("Roubo de veículos", "veic"),
    "furto_veiculo": ("Furto de veículos", "veic"),
    "roubo_carga": ("Roubo de carga", "hab"),
    "armas_apreendidas": ("Armas de fogo apreendidas", "hab"),
    "desaparecidos": ("Pessoas desaparecidas", "hab"),
    "populacao_prisional": ("População no sistema penitenciário", "hab"),
}


def serie_longa(planilha, aba: str) -> pd.DataFrame:
    """Lê uma tabela 'UF × anos' (números absolutos) a partir do cabeçalho de anos."""
    todas = linhas(planilha, aba)
    cab = next(r for r in todas[:10] if len(r) > 1 and r[1] and re.match(r"^\d{4}", str(r[1])))
    anos = []
    for c in cab[1:]:
        # Para no fim da sequência de anos: depois vêm taxas e variações que repetem anos ("2024", "2024-2025").
        if c is None or not re.match(r"^\d{4}$|^\d{4} \(", str(c).strip()) or (anos and int(str(c)[:4]) <= anos[-1]):
            break
        anos.append(int(str(c)[:4]))
    saida = []
    for r in todas:
        if not r or r[0] is None:
            continue
        sigla = "BR" if str(r[0]).strip() == "Total" else nome_uf(r[0])
        if sigla is None or sigla in REGIOES:
            continue
        for i, ano in enumerate(anos):
            saida.append({"sigla_uf": sigla, "ano": ano, "valor": numero(r[1 + i])})
    return pd.DataFrame(saida)


def linha_do_tempo(planilha) -> pd.DataFrame:
    """Uma tabela com todos os indicadores por UF e ano, com taxas na mesma base em todos os anos."""
    mvi = serie_mvi(planilha)
    mvi = mvi[mvi["nivel"] != "regiao"]
    # População: IBGE (base histórica) até 2021; depois, a implícita nas taxas do Anuário (mortes ÷ taxa).
    pop_fbsp = mvi.assign(pop=mvi["mvi"] / mvi["taxa"] * 1e5)[["sigla_uf", "ano", "pop"]]
    rec = recentes(planilha)
    frota_rec = rec[rec["indicador"] == "roubo_veiculo"].assign(frota=lambda t: t["valor"] / t["taxa"] * 1e5)
    historica = pd.read_csv(RAIZ / "seguranca_uf.csv")
    pop = pd.concat([historica[["sigla_uf", "ano", "populacao"]].rename(columns={"populacao": "pop"}),
                     pop_fbsp[pop_fbsp["ano"] > historica["ano"].max()]])
    frota = pd.concat([historica[["sigla_uf", "ano", "frota"]], frota_rec[["sigla_uf", "ano", "frota"]]])
    # Brasil na base histórica: soma dos estados (só quando os 27 informaram).
    soma = historica.groupby("ano")[["populacao", "frota"]].sum().reset_index().assign(sigla_uf="BR")
    pop = pd.concat([pop, soma.rename(columns={"populacao": "pop"})[["sigla_uf", "ano", "pop"]]])
    frota = pd.concat([frota, soma[["sigla_uf", "ano", "frota"]]])

    partes = [mvi.rename(columns={"mvi": "valor"})[["sigla_uf", "ano", "valor", "taxa"]].assign(
        indicador="mvi", rotulo="Mortes violentas intencionais", base="hab", fonte="FBSP, 20º Anuário, Tabela 02")]
    for chave, (aba, rotulo, base) in SERIES_LONGAS.items():
        partes.append(serie_longa(planilha, aba).assign(indicador=chave, rotulo=rotulo, base=base,
                                                        fonte=f"FBSP, 20º Anuário, Tabela {aba[1:]}"))
    prisao = serie_longa_cols(planilha, "T71", 1)  # só o sistema penitenciário, como na base histórica
    for chave, (rotulo, base) in COMBINADAS.items():
        antigo = historica[["sigla_uf", "ano", chave]].rename(columns={chave: "valor"}).dropna()
        completos = antigo.groupby("ano").filter(lambda g: len(g) == 27)
        brasil = completos.groupby("ano", as_index=False)["valor"].sum().assign(sigla_uf="BR")
        antigo = pd.concat([antigo, brasil]).assign(fonte="FBSP, Anuários 2008–2022, via Base dos Dados")
        novo = prisao if chave == "populacao_prisional" else rec[rec["indicador"] == chave][["sigla_uf", "ano", "valor"]]
        novo = novo.assign(fonte="FBSP, 20º Anuário (2026)")
        partes.append(pd.concat([antigo, novo]).assign(indicador=chave, rotulo=rotulo, base=base))
    tabela = pd.concat(partes, ignore_index=True).dropna(subset=["valor"])
    tabela = tabela.merge(pop, on=["sigla_uf", "ano"], how="left").merge(frota, on=["sigla_uf", "ano"], how="left")
    calculada = tabela["valor"] / tabela["pop"] * 1e5
    calculada = calculada.where(tabela["base"] != "veic", tabela["valor"] / tabela["frota"] * 1e5)
    calculada = calculada.where(tabela["base"] != "rs", tabela["valor"] / tabela["pop"])
    calculada = calculada.where(tabela["base"] != "pct", tabela["valor"])
    tabela["taxa"] = tabela["taxa"].fillna(calculada) if "taxa" in tabela else calculada
    colunas = ["indicador", "rotulo", "base", "sigla_uf", "ano", "valor", "taxa", "fonte"]
    repetidos = tabela.duplicated(["indicador", "sigla_uf", "ano"])
    if repetidos.any():
        raise ValueError(f"Linhas repetidas na linha do tempo: {tabela[repetidos].head().to_dict('records')}")
    return tabela[colunas].sort_values(["indicador", "sigla_uf", "ano"]).reset_index(drop=True)


def serie_longa_cols(planilha, aba: str, coluna: int) -> pd.DataFrame:
    """Valores de dois anos lidos a partir de uma coluna (ex.: T71, sistema penitenciário 2024 e 2025)."""
    todas = linhas(planilha, aba)
    ano_a, ano_b = anos_da_tabela(todas, coluna)
    saida = []
    for r in todas:
        sigla = nome_uf(r[0]) if r else None
        if sigla is None or sigla in REGIOES:
            continue
        for ano, desloc in ((ano_a, 0), (ano_b, 1)):
            saida.append({"sigla_uf": sigla, "ano": ano, "valor": numero(r[coluna + desloc])})
    return pd.DataFrame(saida)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    planilha = openpyxl.load_workbook(sys.argv[1], read_only=True, data_only=True)
    for nome, funcao in [("seguranca_mvi_serie", serie_mvi), ("seguranca_uf_recente", recentes),
                         ("seguranca_prisional", prisional), ("seguranca_series", linha_do_tempo)]:
        tabela = funcao(planilha)
        tabela.to_csv(RAIZ / f"{nome}.csv", index=False)
        print(f"{nome}: {len(tabela)} linhas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
