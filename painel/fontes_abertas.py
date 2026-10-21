"""Séries buscadas ao vivo em APIs abertas: FMI (dívida pública), IBGE/SIDRA (IPCA por item) e Banco Central (SGS).

Nenhuma pede chave. Cada função devolve uma tabela longa; as funções `interpreta_*` só convertem
a resposta e são testadas em tests/. O script scripts/atualizar_dados_abertos.py salva retratos
em data/ para o painel não depender das APIs.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import requests

PASTA = Path(__file__).resolve().parent.parent / "data"
TEMPO_LIMITE = 30

# ---------------------------------------------------------------- FMI (DataMapper / World Economic Outlook)

FMI_URL = "https://www.imf.org/external/datamapper/api/v1/{indicador}/{paises}"
FMI_ARQUIVO = PASTA / "fmi_divida.csv"

# código -> (nome, descrição)
FMI_INDICADORES = {
    "GGXWDG_NGDP": ("Dívida bruta do governo geral", "Dívida bruta das três esferas de governo, conceito do FMI."),
    "GGXWDN_NGDP": ("Dívida líquida do governo geral", "Dívida bruta menos ativos financeiros do governo."),
    "GGXONLB_NGDP": ("Resultado primário do governo geral", "Receitas menos despesas, sem juros. Negativo = déficit."),
    "GGXCNL_NGDP": ("Resultado nominal do governo geral", "Resultado com juros. Negativo = déficit."),
}

# código do FMI -> (nome em português, grupo)
FMI_PAISES = {
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
    "GRC": ("Grécia", "Desenvolvidos"),
    "JPN": ("Japão", "Desenvolvidos"),
    "WEOWORLD": ("Mundo", "Média"),
    "ADVEC": ("Economias avançadas", "Média"),
    "OEMDC": ("Emergentes e em desenvolvimento", "Média"),
}


def interpreta_fmi(resposta: dict, indicador: str, ultimo_ano_observado: int) -> pd.DataFrame:
    """Resposta do DataMapper: {"values": {indicador: {pais: {ano: valor}}}}."""
    series = (resposta or {}).get("values", {}).get(indicador, {})
    linhas = []
    for codigo, anos in series.items():
        if codigo not in FMI_PAISES or not isinstance(anos, dict):
            continue
        for ano, valor in anos.items():
            if valor is None:
                continue
            ano = int(ano)
            linhas.append({
                "indicador": indicador, "codigo": codigo, "pais": FMI_PAISES[codigo][0], "grupo": FMI_PAISES[codigo][1],
                "ano": ano, "valor": float(valor), "projecao": ano > ultimo_ano_observado,
            })
    if not linhas:
        raise ValueError(f"FMI sem dados para {indicador}")
    return pd.DataFrame(linhas)


def baixa_fmi(ultimo_ano_observado: int) -> tuple[pd.DataFrame, list[str]]:
    partes, falhas = [], []
    for indicador in FMI_INDICADORES:
        try:
            r = requests.get(FMI_URL.format(indicador=indicador, paises="/".join(FMI_PAISES)), timeout=TEMPO_LIMITE)
            r.raise_for_status()
            partes.append(interpreta_fmi(r.json(), indicador, ultimo_ano_observado))
        except Exception:
            falhas.append(indicador)
    return (pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()), falhas


# ---------------------------------------------------------------- IBGE / SIDRA: IPCA por item

SIDRA_URL = "https://apisidra.ibge.gov.br/values/t/{tabela}/n1/all/v/69/p/{periodos}/c315/all"
SIDRA_ARQUIVO = PASTA / "ipca_itens.csv"
# Tabela 1419: jan/2012 a dez/2019. Tabela 7060: a partir de jan/2020. Variável 69: variação acumulada no ano.
SIDRA_TABELAS = [(1419, 2012, 2019), (7060, 2020, None)]

# nome no painel -> padrão do nome da categoria no SIDRA (sem o código numérico na frente)
ITENS_IPCA = {
    "Índice geral": r"índice geral",
    "Alimentação e bebidas": r"alimentação e bebidas",
    "Alimentação no domicílio": r"alimentação no domicílio",
    "Arroz": r"arroz",
    "Feijão-carioca": r"feijão\s*-\s*carioca.*",
    "Café moído": r"café moído",
    "Leite longa vida": r"leite longa vida",
    "Carnes": r"carnes",
    "Óleo de soja": r"óleo de soja",
    "Tomate": r"tomate",
    "Batata-inglesa": r"batata\s*-\s*inglesa",
    "Pão francês": r"pão francês",
    "Ovo de galinha": r"ovo de galinha",
}


def _nome_categoria(texto: str) -> str:
    """'1101002.Arroz' -> 'arroz'."""
    return re.sub(r"^[\d.]+\s*", "", str(texto)).strip().lower()


def interpreta_sidra(resposta: list) -> pd.DataFrame:
    """A API do SIDRA devolve uma lista: a 1ª linha é o cabeçalho (rótulos das colunas D1C, D2N...)."""
    if not isinstance(resposta, list) or len(resposta) < 2:
        raise ValueError("SIDRA sem dados")
    cabecalho = resposta[0]
    col_mes = next(k for k, rot in cabecalho.items() if k.endswith("C") and str(rot).startswith("Mês"))
    col_cat = next(k for k, rot in cabecalho.items()
                   if k.endswith("N") and str(rot).lower().startswith("geral, grupo"))
    linhas = []
    for linha in resposta[1:]:
        nome = _nome_categoria(linha.get(col_cat, ""))
        item = next((rotulo for rotulo, padrao in ITENS_IPCA.items() if re.fullmatch(padrao, nome)), None)
        try:
            valor = float(str(linha.get("V")).replace(",", "."))
        except ValueError:  # "..." ou "-": sem dado
            continue
        if item is None:
            continue
        periodo = str(linha[col_mes])
        linhas.append({"ano": int(periodo[:4]), "mes": int(periodo[4:6]), "item": item, "variacao_pct": valor})
    if not linhas:
        raise ValueError("SIDRA sem os itens esperados")
    return pd.DataFrame(linhas).drop_duplicates(["ano", "mes", "item"])


def baixa_sidra(ano_final: int) -> pd.DataFrame:
    """Variação acumulada em cada ano fechado (dezembro), por item."""
    partes = []
    for tabela, inicio, fim in SIDRA_TABELAS:
        fim = fim or ano_final
        periodos = ",".join(f"{a}12" for a in range(inicio, fim + 1))
        r = requests.get(SIDRA_URL.format(tabela=tabela, periodos=periodos), timeout=60)
        r.raise_for_status()
        partes.append(interpreta_sidra(r.json()))
    tabela = pd.concat(partes, ignore_index=True)
    return tabela[tabela["mes"] == 12].drop(columns="mes").assign(tipo="oficial", fonte_id="IBGE_SIDRA")


# ---------------------------------------------------------------- Banco Central / SGS

SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
SGS_ARQUIVO = PASTA / "bcb_divida.csv"
SGS_SERIES = {
    13762: "Dívida bruta do governo geral",
    4513: "Dívida líquida do setor público",
}


def interpreta_sgs(resposta: list, serie: str) -> pd.DataFrame:
    """SGS devolve [{"data": "31/01/2020", "valor": "75.8"}, ...]."""
    linhas = []
    for item in resposta or []:
        try:
            linhas.append({"data": pd.to_datetime(item["data"], dayfirst=True), "serie": serie,
                           "valor": float(item["valor"])})
        except (KeyError, ValueError, TypeError):
            continue
    if not linhas:
        raise ValueError(f"SGS sem dados para {serie}")
    return pd.DataFrame(linhas)


def baixa_sgs() -> pd.DataFrame:
    partes = []
    for codigo, nome in SGS_SERIES.items():
        r = requests.get(SGS_URL.format(codigo=codigo), params={"formato": "json"}, timeout=TEMPO_LIMITE)
        r.raise_for_status()
        partes.append(interpreta_sgs(r.json(), nome))
    return pd.concat(partes, ignore_index=True)


def retrato(arquivo: Path, datas: list[str] | None = None) -> pd.DataFrame | None:
    if arquivo.exists():
        return pd.read_csv(arquivo, parse_dates=datas or False)
    return None
