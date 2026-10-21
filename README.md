# Brasil em dados, 1995–2026

Painel interativo com indicadores econômicos, sociais e fiscais do Brasil e comparações internacionais,
feito com [Streamlit](https://streamlit.io) e [Plotly](https://plotly.com/python/). O visual segue o site
[IDH Brasil](https://gab-berger.github.io/idh-brasil/): fundo limpo, títulos discretos, paleta Okabe-Ito
(segura para daltonismo), o Brasil sempre em laranja e modo escuro automático.

## Abas

| Aba | O que mostra |
|---|---|
| Visão geral | PIB, IPCA, desemprego, IDH, expectativa de vida; PIB e inflação 1995–2025 com as quatro fases do período e médias por fase |
| Social | Renda, Gini e pobreza 1995 × 2024 (Ipea); educação: analfabetismo por recorte, Ideb, Pisa × OCDE, gasto e metas do PNE |
| Poder de compra | Cestas básicas por salário mínimo ano a ano, carne, gasolina, energia e preços de itens da cesta |
| Tributação | Carga tributária do Brasil × Europa, EUA, emergentes e médias; composição consumo × renda × OCDE |
| Contas públicas | Resultado primário, dívida bruta, juros × déficit, gasto por função × referências internacionais, orçamento e Bolsa Família |
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
- Aba Mundo: dados do [Banco Mundial](https://data.worldbank.org) (World Development Indicators), consultados ao vivo
  e guardados em cache por 24 horas. Para salvar um retrato e não depender da API:

  ```sh
  python scripts/atualizar_banco_mundial.py   # grava data/banco_mundial.csv
  ```

  Com esse arquivo presente, o painel usa o retrato salvo; apague-o para voltar à consulta ao vivo.

Valores marcados como `serie_historica` vêm de séries oficiais ainda não reconferidas ponto a ponto. Valide no
SIDRA/IBGE, no Tesouro Transparente e no SGS/BCB antes de uma publicação formal.

## Estrutura

```
streamlit_app.py          cabeçalho, filtros e abas
painel/dados.py           leitura das tabelas
painel/visual.py          cores, CSS, cartões e ajustes dos gráficos
painel/banco_mundial.py   cliente da API do Banco Mundial
painel/secoes/*.py        uma aba por arquivo
scripts/                  atualização do retrato do Banco Mundial
.streamlit/config.toml    tema claro e escuro
```
