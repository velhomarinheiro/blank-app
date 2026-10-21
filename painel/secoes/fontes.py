"""Aba Fontes e método."""

from __future__ import annotations

import streamlit as st

from painel import dados as d
from painel import visual as v

RESSALVAS = [
    ("Séries de domicílios", "PNAD até 2015 e PNAD Contínua depois; comparações longas são indicativas."),
    ("IDH", "O valor de 1990 (0,590) segue metodologia anterior; a comparação com 2023 é só indicativa."),
    ("Pobreza", "As linhas do Ipea (US$ 3 e US$ 8,30 por dia, PPC 2021) diferem das do IBGE. Os dois critérios "
                "aparecem no painel."),
    ("Cesta básica", "A referência é São Paulo (em geral a mais cara). 1995–2016, 2020 e 2024 são médias anuais; "
                     "os demais anos são meses de referência. 2019 ficou sem dado e não foi interpolado."),
    ("Carne", "Não há série pública anual contínua. Picanha (IEA-SP) cobre 2007–2024; carne de primeira tem só "
              "dois pontos (estimativas). O corte muda muito o resultado."),
    ("Gasolina e energia", "Sem série confiável antes de 2002. Tarifas de energia divergem conforme a fonte "
                           "(ano-base e bandeiras)."),
    ("Carga tributária", "32,40% (Tesouro, 2025) e 33,7% (OCDE, 2024) usam metodologias diferentes. Dados OCDE de "
                         "2024 são preliminares; Argentina (2023) e África do Sul (2022) têm anos anteriores."),
    ("Contas públicas", "O resultado primário refere-se ao governo central; o COFOG cobre as três esferas. "
                        "Revisões do PIB podem alterar casas decimais."),
    ("Dívida bruta", "Conceito do Banco Central. No conceito do FMI (inclui títulos na carteira do BC) os valores "
                     "são maiores: 93,4% do PIB em dez/2025."),
    ("Segurança pública", "Os registros vêm das polícias de cada estado, compilados pelo Fórum Brasileiro de Segurança "
                          "Pública. A qualidade varia entre estados e anos, e crimes como estupro têm forte "
                          "subnotificação. A base por estado vai até 2021; 2022–2025 vêm dos Anuários publicados, que "
                          "revisam anos anteriores. Taxas por habitante e por veículo são cálculo próprio."),
    ("Banco Mundial", "Os dados internacionais da aba Mundo vêm da API aberta do Banco Mundial e podem diferir "
                      "das fontes nacionais (revisões, metodologia, anos de referência)."),
]


def mostra(inicio: int, fim: int, tipos: list[str]) -> None:
    st.markdown("### Grau de confiança de cada valor")
    v.kpis([
        {"rotulo": "Oficial", "valor": "●", "detalhe": "valor publicado pela fonte indicada"},
        {"rotulo": "Série histórica", "valor": "●",
         "detalhe": "série oficial conhecida, não reconferida ponto a ponto; valide no SIDRA, Tesouro e SGS/BCB"},
        {"rotulo": "Cálculo próprio", "valor": "○", "detalhe": "conta a partir de dados da fonte (ex.: salário ÷ cesta)"},
        {"rotulo": "Estimativa", "valor": "◇", "detalhe": "estimativa de imprensa ou terceiros"},
    ])
    v.nota("Use o filtro “Tipo de dado”, no topo, para esconder cálculos ou estimativas em todos os gráficos.")

    st.markdown("### Ressalvas de método")
    for titulo, texto in RESSALVAS:
        v.leitura(f"**{titulo}.** {texto}")

    st.markdown("### Fontes")
    st.dataframe(
        d.fontes(),
        hide_index=True,
        width="stretch",
        column_config={
            "fonte_id": st.column_config.TextColumn("Código"),
            "descricao": st.column_config.TextColumn("Fonte", width="large"),
            "url": st.column_config.LinkColumn("Endereço"),
        },
    )
    st.download_button("Baixar todos os dados (JSON)", (d.PASTA_DADOS / "dados.json").read_bytes(),
                       file_name="dados_brasil.json", mime="application/json")
    v.nota("Pacote de dados exportado em 20/10/2026. Cada gráfico do painel tem um “Ver dados” com a tabela e o "
           "download em CSV.")
