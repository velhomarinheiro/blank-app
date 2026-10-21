"""Carga das séries ao vivo, com cache de 24 horas e reserva quando a API não responde.

Ordem de preferência: retrato salvo em data/ (scripts/atualizar_dados_abertos.py) → API ao vivo → dados
conferidos que já vêm no pacote. Uma falha não entra no cache: a próxima visita tenta a API de novo.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from painel import dados as d
from painel import fontes_abertas as fa

DIA = 24 * 3600


def tenta(chave: str, funcao):
    """Chama a API uma vez por sessão: depois de uma falha, não tenta de novo a cada clique."""
    marca = f"api_falhou_{chave}"
    if st.session_state.get(marca):
        raise RuntimeError(f"{chave} indisponível nesta sessão")
    try:
        return funcao()
    except Exception:
        st.session_state[marca] = True
        raise


@st.cache_data(ttl=DIA, show_spinner="Buscando dados do FMI…")
def _fmi_api() -> tuple[pd.DataFrame, list[str]]:
    tabela, falhas = fa.baixa_fmi(ultimo_ano_observado=date.today().year - 1)
    if tabela.empty:
        raise RuntimeError("FMI sem resposta")
    return tabela, falhas


def fmi() -> tuple[pd.DataFrame, str]:
    """Dívida e resultado fiscal por país (FMI). Tabela vazia se não houver como obter."""
    salvo = fa.retrato(fa.FMI_ARQUIVO)
    if salvo is not None and not salvo.empty:
        return salvo, "retrato salvo em data/fmi_divida.csv"
    try:
        tabela, falhas = tenta("fmi", _fmi_api)
        origem = "API do FMI (DataMapper), consulta ao vivo"
        if falhas:
            origem += "; sem resposta para " + ", ".join(falhas)
        return tabela, origem
    except Exception:
        return pd.DataFrame(), ""


@st.cache_data(ttl=DIA, show_spinner="Buscando o IPCA por item no IBGE…")
def _sidra_api() -> pd.DataFrame:
    return fa.baixa_sidra(ano_final=date.today().year - 1)


def ipca_itens() -> tuple[pd.DataFrame, str]:
    """Variação anual do IPCA por item. Completa via IBGE; senão, os pontos conferidos do pacote."""
    salvo = fa.retrato(fa.SIDRA_ARQUIVO)
    if salvo is not None and not salvo.empty:
        return salvo, "IBGE/SIDRA (retrato salvo em data/ipca_itens.csv)"
    try:
        return tenta("sidra", _sidra_api), "IBGE/SIDRA, consulta ao vivo"
    except Exception:
        base = d.tabela("inflacao_alimentos_ipca")
        # O índice geral vem da série macro do pacote.
        geral = d.tabela("macro_pib_ipca_anual")
        geral = geral[geral["ano"] >= base["ano"].min()]
        geral = pd.DataFrame({"ano": geral["ano"], "item": "Índice geral", "variacao_pct": geral["ipca_anual_pct"],
                              "tipo": geral["tipo"], "fonte_id": "IBGE_IPCA"})
        return pd.concat([geral, base], ignore_index=True), "pontos conferidos em divulgações do IBGE (sem acesso ao SIDRA agora)"


@st.cache_data(ttl=DIA, show_spinner="Buscando séries do Banco Central…")
def _sgs_api() -> pd.DataFrame:
    return fa.baixa_sgs()


def bcb_divida() -> tuple[pd.DataFrame, str]:
    """Dívida bruta e líquida mensais (% do PIB). Tabela vazia se o Banco Central não responder."""
    salvo = fa.retrato(fa.SGS_ARQUIVO, datas=["data"])
    if salvo is not None and not salvo.empty:
        return salvo, "retrato salvo em data/bcb_divida.csv"
    try:
        return tenta("sgs", _sgs_api), "Banco Central (SGS), consulta ao vivo"
    except Exception:
        return pd.DataFrame(), ""
