"""Testes rápidos: python -m pytest tests"""

import pytest

from painel import banco_mundial as bm
from painel import visual as v


def resposta(valores):
    """Imita o formato da API do Banco Mundial: [metadados, linhas]."""
    return [
        {"page": 1, "pages": 1, "per_page": 20000, "total": len(valores)},
        [
            {
                "indicator": {"id": "SP.DYN.LE00.IN", "value": "Life expectancy at birth, total (years)"},
                "country": {"id": iso2, "value": "x"},
                "countryiso3code": iso3,
                "date": str(ano),
                "value": valor,
                "unit": "",
                "obs_status": "",
                "decimal": 1,
            }
            for iso2, iso3, ano, valor in valores
        ],
    ]


def test_interpreta_converte_e_descarta_vazios():
    tabela = bm.interpreta(resposta([
        ("BR", "BRA", 2023, 75.8),
        ("BR", "BRA", 2024, None),      # sem valor: descartado
        ("AR", "ARG", 2023, 77.4),
        ("ZZ", "ZZZ", 2023, 50.0),      # fora da lista: descartado
        ("1W", "WLD", 2023, 73.2),
    ]))
    assert list(tabela["pais"]) == ["Brasil", "Argentina", "Mundo"]
    assert list(tabela["grupo"]) == ["Brasil", "América Latina", "Média"]
    assert tabela["ano"].tolist() == [2023, 2023, 2023]


def test_interpreta_recusa_resposta_de_erro():
    with pytest.raises(ValueError):
        bm.interpreta([{"message": [{"id": "120", "value": "Invalid value"}]}])


def test_numeros_no_padrao_brasileiro():
    assert v.br(1234.5, 1) == "1.234,5"
    assert v.br(-0.48, 2) == "−0,48"
    assert v.br(6.79, 1, sinal=True) == "+6,8"
    assert v.br(None) == "—"


# ---------------------------------------------------------------- FMI, IBGE e Banco Central

from painel import fontes_abertas as fa  # noqa: E402


def test_fmi_marca_projecoes_e_ignora_codigos_desconhecidos():
    resposta = {"values": {"GGXWDG_NGDP": {
        "BRA": {"2024": 87.3, "2025": 91.4, "2026": 94.0},
        "XYZ": {"2024": 10.0},
        "WEOWORLD": {"2025": None},
    }}, "api": {"version": "1"}}
    tabela = fa.interpreta_fmi(resposta, "GGXWDG_NGDP", ultimo_ano_observado=2025)
    assert set(tabela["pais"]) == {"Brasil"}
    assert tabela.set_index("ano")["projecao"].to_dict() == {2024: False, 2025: False, 2026: True}


def test_fmi_sem_valores_falha():
    with pytest.raises(ValueError):
        fa.interpreta_fmi({"values": {}}, "GGXWDG_NGDP", 2025)


def test_sidra_acha_colunas_pelo_cabecalho_e_casa_nomes():
    cab = {"NC": "Nível Territorial (Código)", "V": "Valor", "D1N": "Brasil", "D2N": "Variável",
           "D3C": "Mês (Código)", "D3N": "Mês", "D4C": "Geral, grupo, subgrupo, item e subitem (Código)",
           "D4N": "Geral, grupo, subgrupo, item e subitem"}
    linha = lambda mes, cat, valor: {"V": valor, "D3C": mes, "D4N": cat}  # noqa: E731
    tabela = fa.interpreta_sidra([
        cab,
        linha("202412", "Índice geral", "4.83"),
        linha("202412", "1.Alimentação e bebidas", "7.69"),
        linha("202412", "1101002.Arroz", "8.24"),
        linha("202412", "1101073.Feijão - carioca (rajado)", "-4.1"),
        linha("202412", "1107099.Café moído", "39.6"),
        linha("202412", "1101001.Arroz integral", "1.0"),   # não é o subitem procurado
        linha("202412", "1104.Carnes", "..."),              # sem dado
    ])
    obtido = tabela.set_index("item")["variacao_pct"].to_dict()
    assert obtido == {"Índice geral": 4.83, "Alimentação e bebidas": 7.69, "Arroz": 8.24,
                      "Feijão-carioca": -4.1, "Café moído": 39.6}
    assert set(tabela["ano"]) == {2024} and set(tabela["mes"]) == {12}


def test_sgs_converte_datas_e_valores():
    tabela = fa.interpreta_sgs([{"data": "01/12/2025", "valor": "78.7"}, {"data": "x", "valor": "1"}], "DBGG")
    assert len(tabela) == 1
    assert tabela.iloc[0]["data"].month == 12 and tabela.iloc[0]["valor"] == 78.7


# ---------------------------------------------------------------- Segurança

import pandas as pd  # noqa: E402

from painel.secoes import seguranca as seg  # noqa: E402


def test_taxas_de_seguranca():
    t = pd.DataFrame({"mvi": [50.0], "roubo_veiculo": [30.0], "populacao": [200_000], "frota": [60_000]})
    assert seg.taxa(t, "mvi").iloc[0] == 25.0              # por 100 mil habitantes
    assert seg.taxa(t, "roubo_veiculo").iloc[0] == 5.0     # por 10 mil veículos


def test_brasil_so_soma_anos_com_todos_os_estados():
    linhas = [{"ano": 2020, "sigla_uf": f"U{i}", "mvi": 10.0, "populacao": 100_000, "frota": 1} for i in range(27)]
    linhas += [{"ano": 2021, "sigla_uf": f"U{i}", "mvi": 10.0, "populacao": 100_000, "frota": 1} for i in range(26)]
    nacional = seg.brasil(pd.DataFrame(linhas), "mvi")
    assert list(nacional["ano"]) == [2020]
    assert nacional["valor"].iloc[0] == 10.0


def test_base_de_seguranca_bate_com_o_anuario():
    """Totais nacionais conhecidos do Fórum: 64.078 mortes violentas em 2017 e 47.503 em 2021."""
    uf = pd.read_csv("data/dados/seguranca_uf.csv")
    total = uf.groupby("ano")["mvi"].sum()
    assert total[2017] == 64078 and total[2021] == 47503
    assert uf.groupby("ano")["sigla_uf"].nunique().eq(27).all()
