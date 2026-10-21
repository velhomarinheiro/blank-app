"""Comparativo internacional com a API aberta do Banco Mundial (World Development Indicators).

A API é pública e não pede chave: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
O painel tenta primeiro um retrato salvo em data/banco_mundial.csv (gerado por
scripts/atualizar_banco_mundial.py) e, se ele não existir, consulta a API ao vivo.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

URL = "https://api.worldbank.org/v2/country/{paises}/indicator/{indicador}"
ARQUIVO = Path(__file__).resolve().parent.parent / "data" / "banco_mundial.csv"
ANO_INICIAL = 1990

# código -> (nome curto, unidade, casas decimais, descrição)
INDICADORES = {
    "NY.GDP.PCAP.PP.KD": ("PIB per capita (PPC)", "US$ internacionais de 2021", 0,
                          "PIB por habitante em paridade de poder de compra, a preços constantes."),
    "NY.GDP.MKTP.KD.ZG": ("Crescimento do PIB", "% ao ano", 1, "Crescimento real anual do PIB."),
    "FP.CPI.TOTL.ZG": ("Inflação ao consumidor", "% ao ano", 1, "Variação anual do índice de preços ao consumidor."),
    "SL.UEM.TOTL.ZS": ("Desemprego", "% da força de trabalho", 1, "Estimativa modelada da OIT."),
    "SP.DYN.LE00.IN": ("Expectativa de vida", "anos", 1, "Expectativa de vida ao nascer."),
    "SP.DYN.IMRT.IN": ("Mortalidade infantil", "por mil nascidos vivos", 1, "Óbitos antes de 1 ano por mil nascidos vivos."),
    "SI.POV.GINI": ("Índice de Gini", "0–100", 1, "Desigualdade de renda ou consumo (estimativa do Banco Mundial)."),
    "SI.POV.DDAY": ("Extrema pobreza", "% da população", 1, "População abaixo da linha internacional de pobreza extrema."),
    "SE.XPD.TOTL.GD.ZS": ("Gasto público em educação", "% do PIB", 1, "Despesa pública total com educação."),
    "SH.XPD.CHEX.GD.ZS": ("Gasto total em saúde", "% do PIB", 1, "Despesa corrente em saúde (pública e privada)."),
    "MS.MIL.XPND.GD.ZS": ("Gasto militar", "% do PIB", 1, "Despesa militar (dados do SIPRI)."),
    "GC.DOD.TOTL.GD.ZS": ("Dívida do governo central", "% do PIB", 1, "Dívida bruta do governo central."),
}

# código ISO3 -> (nome em português, grupo)
PAISES = {
    "BRA": ("Brasil", "Brasil"),
    "ARG": ("Argentina", "América Latina"),
    "CHL": ("Chile", "América Latina"),
    "COL": ("Colômbia", "América Latina"),
    "MEX": ("México", "América Latina"),
    "PER": ("Peru", "América Latina"),
    "URY": ("Uruguai", "América Latina"),
    "CHN": ("China", "BRICS"),
    "IND": ("Índia", "BRICS"),
    "RUS": ("Rússia", "BRICS"),
    "ZAF": ("África do Sul", "BRICS"),
    "IDN": ("Indonésia", "Emergentes"),
    "TUR": ("Turquia", "Emergentes"),
    "KOR": ("Coreia do Sul", "Desenvolvidos"),
    "USA": ("Estados Unidos", "Desenvolvidos"),
    "CAN": ("Canadá", "Desenvolvidos"),
    "DEU": ("Alemanha", "Desenvolvidos"),
    "FRA": ("França", "Desenvolvidos"),
    "GBR": ("Reino Unido", "Desenvolvidos"),
    "ITA": ("Itália", "Desenvolvidos"),
    "ESP": ("Espanha", "Desenvolvidos"),
    "PRT": ("Portugal", "Desenvolvidos"),
    "JPN": ("Japão", "Desenvolvidos"),
    "WLD": ("Mundo", "Média"),
    "LCN": ("América Latina e Caribe", "Média"),
    "OED": ("Membros da OCDE", "Média"),
}


def interpreta(resposta: list) -> pd.DataFrame:
    """Converte a resposta JSON da API ([metadados, linhas]) numa tabela longa."""
    if not isinstance(resposta, list) or len(resposta) < 2 or not resposta[1]:
        mensagem = resposta[0].get("message") if isinstance(resposta, list) and resposta else resposta
        raise ValueError(f"Resposta sem dados do Banco Mundial: {mensagem}")
    linhas = []
    for item in resposta[1]:
        if item.get("value") is None:
            continue
        codigo = item.get("countryiso3code") or item["country"]["id"]
        if codigo not in PAISES:
            continue
        linhas.append(
            {
                "indicador": item["indicator"]["id"],
                "iso3": codigo,
                "pais": PAISES[codigo][0],
                "grupo": PAISES[codigo][1],
                "ano": int(item["date"]),
                "valor": float(item["value"]),
            }
        )
    return pd.DataFrame(linhas)


def baixa_indicador(indicador: str, ano_final: int, tempo_limite: float = 30) -> pd.DataFrame:
    paises = ";".join(PAISES)
    resposta = requests.get(
        URL.format(paises=paises, indicador=indicador),
        params={"format": "json", "per_page": 20000, "date": f"{ANO_INICIAL}:{ano_final}"},
        timeout=tempo_limite,
    )
    resposta.raise_for_status()
    return interpreta(resposta.json())


def baixa_tudo(ano_final: int) -> tuple[pd.DataFrame, list[str]]:
    """Baixa todos os indicadores. Devolve a tabela e a lista de indicadores que falharam."""
    partes, falhas = [], []
    for codigo in INDICADORES:
        try:
            partes.append(baixa_indicador(codigo, ano_final))
        except Exception:  # um indicador fora do ar não derruba os outros
            falhas.append(codigo)
    if not partes:
        return pd.DataFrame(columns=["indicador", "iso3", "pais", "grupo", "ano", "valor"]), falhas
    return pd.concat(partes, ignore_index=True), falhas


def retrato_salvo() -> pd.DataFrame | None:
    if ARQUIVO.exists():
        return pd.read_csv(ARQUIVO)
    return None
