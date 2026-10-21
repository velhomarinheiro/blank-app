"""Prepara os dados da aba Segurança a partir das tabelas abertas da Base dos Dados.

    pip install shapely   # só para o mapa
    python scripts/preparar_seguranca.py

Fontes (download direto, sem chave):
- Anuário Brasileiro de Segurança Pública (FBSP), por UF, 2007–2021: br_fbsp_absp/uf
- População por UF (IBGE): br_ibge_populacao/uf
- Frota de veículos por UF (Denatran/Senatran): br_denatran_frota/uf_tipo
- Malha das UFs (IBGE, via geobr): br_geobr_mapas/uf

Grava data/dados/seguranca_uf.csv e data/geo/uf.geojson.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pandas as pd

BASE = "https://storage.googleapis.com/basedosdados-public/one-click-download"
RAIZ = Path(__file__).resolve().parent.parent
SAIDA_UF = RAIZ / "data" / "dados" / "seguranca_uf.csv"
SAIDA_MAPA = RAIZ / "data" / "geo" / "uf.geojson"

UFS = {
    "AC": ("Acre", "Norte"), "AL": ("Alagoas", "Nordeste"), "AM": ("Amazonas", "Norte"), "AP": ("Amapá", "Norte"),
    "BA": ("Bahia", "Nordeste"), "CE": ("Ceará", "Nordeste"), "DF": ("Distrito Federal", "Centro-Oeste"),
    "ES": ("Espírito Santo", "Sudeste"), "GO": ("Goiás", "Centro-Oeste"), "MA": ("Maranhão", "Nordeste"),
    "MG": ("Minas Gerais", "Sudeste"), "MS": ("Mato Grosso do Sul", "Centro-Oeste"), "MT": ("Mato Grosso", "Centro-Oeste"),
    "PA": ("Pará", "Norte"), "PB": ("Paraíba", "Nordeste"), "PE": ("Pernambuco", "Nordeste"), "PI": ("Piauí", "Nordeste"),
    "PR": ("Paraná", "Sul"), "RJ": ("Rio de Janeiro", "Sudeste"), "RN": ("Rio Grande do Norte", "Nordeste"),
    "RO": ("Rondônia", "Norte"), "RR": ("Roraima", "Norte"), "RS": ("Rio Grande do Sul", "Sul"),
    "SC": ("Santa Catarina", "Sul"), "SE": ("Sergipe", "Nordeste"), "SP": ("São Paulo", "Sudeste"),
    "TO": ("Tocantins", "Norte"),
}

# coluna de saída -> colunas somadas da tabela do FBSP
INDICADORES = {
    "mvi": ["quantidade_morte_violenta_intencional"],
    "homicidio_doloso": ["quantidade_vitima_homicidio_doloso"],
    "latrocinio": ["quantidade_latrocinio"],
    "lesao_corporal_morte": ["quantidade_lesao_corporal_seguida_de_morte"],
    "feminicidio": ["quantidade_feminicidio"],
    "estupro": ["quantidade_estupro"],
    "roubo_veiculo": ["quantidade_roubo_de_veiculo"],
    "furto_veiculo": ["quantidade_furto_veiculo"],
    "roubo_carga": ["quantidade_roubo_carga"],
    "morte_intervencao_policial": [
        "quantidade_morte_intervencao_policial_civil_servico", "quantidade_morte_intervencao_policial_civil_fora_servico",
        "quantidade_morte_intervencao_policial_militar_servico", "quantidade_morte_intervencao_policial_militar_fora_servico",
    ],
    "policiais_mortos": [
        "quantidade_policial_civil_morto_confronto_servico", "quantidade_policial_civil_morto_confronto_fora_servico",
        "quantidade_policial_militar_morto_confronto_servico", "quantidade_policial_militar_morto_confronto_fora_servico",
    ],
    "armas_apreendidas": ["quantidade_arma_fogo_apreendida"],
    "desaparecidos": ["quantidade_registro_pessoa_desaparecida"],
    "suicidio": ["quantidade_suicidio"],
    "populacao_prisional": ["quantidade_populacao_sistema_penitenciario"],
    "despesa_seguranca": ["despesa_empenhada_seguranca_publica"],
}
# Indicadores que podem ser zero de verdade num estado pequeno. Nos demais, zero significa "sem dado".
PODEM_SER_ZERO = {"latrocinio", "policiais_mortos", "roubo_carga", "lesao_corporal_morte"}


def le(caminho: str) -> pd.DataFrame:
    return pd.read_csv(f"{BASE}/{caminho}", engine="python")


def limpa(fbsp: pd.DataFrame) -> pd.DataFrame:
    """Soma as colunas de cada indicador e trata como lacuna o que é zero por falta de coleta."""
    saida = fbsp[["ano", "sigla_uf"]].copy()
    for nome, colunas in INDICADORES.items():
        partes = fbsp[colunas]
        valor = partes.sum(axis=1, min_count=1)
        # Ano em que todos os estados vêm zerados: série ainda não coletada.
        zerado_no_ano = valor.groupby(fbsp["ano"]).transform(lambda s: (s.fillna(0) == 0).all())
        valor = valor.mask(zerado_no_ano)
        if nome not in PODEM_SER_ZERO:
            valor = valor.mask(valor == 0)
        saida[nome] = valor
    return saida


def frota_por_ano(frota: pd.DataFrame) -> pd.DataFrame:
    """Frota total no último mês disponível de cada ano."""
    frota = frota.sort_values(["sigla_uf", "ano", "mes"])
    return frota.groupby(["sigla_uf", "ano"], as_index=False).last()[["sigla_uf", "ano", "total"]].rename(
        columns={"total": "frota"})


def mapa(geo: pd.DataFrame) -> dict:
    from shapely import wkt
    from shapely.geometry import MultiPolygon, Polygon, mapping
    from shapely.geometry.polygon import orient

    def horario(forma):
        # O Plotly (d3-geo) espera o anel externo no sentido horário; no anti-horário pinta o mundo todo.
        if isinstance(forma, Polygon):
            return orient(forma, sign=-1.0)
        if isinstance(forma, MultiPolygon):
            return MultiPolygon([orient(p, sign=-1.0) for p in forma.geoms])
        return forma

    feicoes = []
    for _, linha in geo.iterrows():
        forma = horario(wkt.loads(linha["geometria"]).simplify(0.05, preserve_topology=True))
        geometria = mapping(forma)
        # Arredonda coordenadas para deixar o arquivo leve.
        geometria = json.loads(json.dumps(geometria), parse_float=lambda x: round(float(x), 3))
        feicoes.append({"type": "Feature", "id": linha["sigla_uf"], "properties": {"sigla_uf": linha["sigla_uf"]},
                        "geometry": geometria})
    return {"type": "FeatureCollection", "features": feicoes}


def main() -> int:
    fbsp = limpa(le("br_fbsp_absp/uf/uf.csv.gz"))
    pop = le("br_ibge_populacao/uf/uf.csv.gz")[["sigla_uf", "ano", "populacao"]]
    frota = frota_por_ano(le("br_denatran_frota/uf_tipo/uf_tipo.csv.gz"))
    tabela = fbsp.merge(pop, on=["sigla_uf", "ano"], how="left").merge(frota, on=["sigla_uf", "ano"], how="left")
    tabela.insert(2, "uf", tabela["sigla_uf"].map(lambda s: UFS[s][0]))
    tabela.insert(3, "regiao", tabela["sigla_uf"].map(lambda s: UFS[s][1]))
    tabela = tabela.sort_values(["ano", "sigla_uf"])
    tabela.to_csv(SAIDA_UF, index=False, float_format="%.0f")
    print(f"{len(tabela)} linhas em {SAIDA_UF} ({tabela['ano'].min()}–{tabela['ano'].max()})")

    try:
        csv.field_size_limit(sys.maxsize)
        SAIDA_MAPA.parent.mkdir(parents=True, exist_ok=True)
        SAIDA_MAPA.write_text(json.dumps(mapa(le("br_geobr_mapas/uf/uf.csv.gz")), separators=(",", ":")))
        print(f"Mapa em {SAIDA_MAPA} ({SAIDA_MAPA.stat().st_size // 1024} KB)")
    except ImportError:
        print("Mapa não gerado: instale shapely (pip install shapely).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
