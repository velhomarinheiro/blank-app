"""Leitura das tabelas do pacote de dados (pasta data/)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

PASTA_DADOS = Path(__file__).resolve().parent.parent / "data"

# Rótulos da coluna `tipo` (grau de confiança de cada valor).
TIPOS = {
    "oficial": "Oficial",
    "serie_historica": "Série histórica",
    "calculo": "Cálculo",
    "estimativa": "Estimativa",
}


@st.cache_data
def tabela(nome: str) -> pd.DataFrame:
    """Lê uma tabela de data/dados/<nome>.csv."""
    return pd.read_csv(PASTA_DADOS / "dados" / f"{nome}.csv")


@st.cache_data
def fontes() -> pd.DataFrame:
    return pd.read_csv(PASTA_DADOS / "fontes.csv").fillna("")


def valor(df: pd.DataFrame, **filtros) -> float:
    """Primeiro valor de `valor` que casa com os filtros (coluna=valor)."""
    linhas = df
    for coluna, esperado in filtros.items():
        linhas = linhas[linhas[coluna] == esperado]
    if linhas.empty:
        raise KeyError(f"Sem linha para {filtros}")
    return float(linhas.iloc[0]["valor"])


def filtra_tipos(df: pd.DataFrame, tipos: list[str], coluna: str = "tipo") -> pd.DataFrame:
    """Mantém só as linhas cujo tipo foi escolhido no filtro. Linhas sem tipo (lacunas) ficam."""
    return df[df[coluna].isna() | df[coluna].isin(tipos)]


def filtra_periodo(df: pd.DataFrame, inicio: int, fim: int, coluna: str = "ano") -> pd.DataFrame:
    anos = pd.to_numeric(df[coluna], errors="coerce")
    return df[anos.between(inicio, fim)]
