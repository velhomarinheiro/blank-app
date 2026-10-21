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
