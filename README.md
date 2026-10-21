# Brasil em dados, 1995–2026

Painel interativo com indicadores econômicos, sociais e fiscais do Brasil e comparações internacionais,
feito com [Streamlit](https://streamlit.io) e [Plotly](https://plotly.com/python/). O visual segue o site
[IDH Brasil](https://gab-berger.github.io/idh-brasil/): fundo limpo, títulos discretos, paleta Okabe-Ito
(segura para daltonismo), o Brasil sempre em laranja e modo escuro automático.

## Abas

| Aba | O que mostra |
|---|---|
| Visão geral | PIB, IPCA, desemprego, IDH, expectativa de vida; PIB e inflação 1995–2025 com as quatro fases do período e médias por fase |
| Social | Renda, Gini e pobreza 1995 × 2024 (Ipea); educação: analfabetismo por recorte, Ideb, Pisa 2000–2025 × média da OCDE, gasto e metas do PNE |
| Poder de compra | Cestas básicas por salário mínimo ano a ano, carne, gasolina, energia e inflação anual dos alimentos por item (IPCA) |
| Tributação | Carga tributária do Brasil × Europa, EUA, emergentes e médias; composição consumo × renda × OCDE |
| Contas públicas | Resultado primário, dívida bruta e líquida mês a mês (Banco Central), dívida e resultado fiscal de 25 países e médias (FMI, com projeções), gasto por função, orçamento e Bolsa Família |
| Mundo | Comparativo internacional com a API aberta do Banco Mundial (12 indicadores, 25 países e médias) |
| Fontes e método | Grau de confiança dos dados, ressalvas de método e lista de fontes com links |

Filtros no topo: **período** e **tipo de dado** (oficial, série histórica, cálculo, estimativa). Cálculos aparecem
com marcador vazado ou barra clara; estimativas, com losango vazado ou barra hachurada. Cada gráfico tem um
"Ver dados" com a tabela e o download em CSV.

## Como rodar

```sh
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Testes rápidos: `pip install pytest && python -m pytest tests`.

## Publicar

No [Streamlit Community Cloud](https://share.streamlit.io): **New app** → este repositório → arquivo
`streamlit_app.py`. Não precisa de chave nem segredo.

## Dados

- `data/dados/*.csv` e `data/dados.json`: as 15 tabelas do pacote de dados (exportado em 20/10/2026), com a coluna
  `tipo` e o código da fonte em cada linha. `data/fontes.csv` lista as fontes; `data/LEIAME_pacote.md` traz a
  descrição original e as ressalvas.
- Séries buscadas ao vivo em APIs abertas, sem chave, com cache de 24 horas:
  - **Banco Mundial** (aba Mundo): 12 indicadores, 25 países e médias.
  - **FMI** (Contas públicas): dívida bruta e líquida, resultado primário e nominal do governo geral, com projeções.
  - **IBGE/SIDRA** (Poder de compra): IPCA anual por item, tabelas 1419 e 7060.
  - **Banco Central/SGS** (Contas públicas): dívida bruta (13762) e líquida (4513), mês a mês.

  Se uma API não responder, o painel mostra os dados conferidos do pacote (`data/dados/inflacao_alimentos_ipca.csv`,
  `data/dados/divida_internacional_destaques.csv`) ou um aviso. Para salvar retratos e não depender das APIs:

  ```sh
  python scripts/atualizar_dados_abertos.py   # grava data/banco_mundial.csv, fmi_divida.csv, ipca_itens.csv, bcb_divida.csv
  ```

  Com um retrato presente, o painel usa ele; apague o arquivo para voltar à consulta ao vivo.
- `data/dados/pisa_historico.csv`: Pisa 2000–2025, Brasil e média da OCDE (Inep e OCDE).

Valores marcados como `serie_historica` vêm de séries oficiais ainda não reconferidas ponto a ponto. Valide no
SIDRA/IBGE, no Tesouro Transparente e no SGS/BCB antes de uma publicação formal.

## Estrutura

```
streamlit_app.py          cabeçalho, filtros e abas
painel/dados.py           leitura das tabelas
painel/visual.py          cores, CSS, cartões e ajustes dos gráficos
painel/banco_mundial.py   cliente da API do Banco Mundial
painel/fontes_abertas.py  clientes do FMI, IBGE/SIDRA e Banco Central
painel/carga.py           cache e reservas das séries ao vivo
painel/secoes/*.py        uma aba por arquivo
scripts/                  atualização dos retratos das APIs
.streamlit/config.toml    tema claro e escuro
```
