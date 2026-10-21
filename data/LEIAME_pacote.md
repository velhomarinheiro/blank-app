# Pacote de dados — Brasil 1995–2026: indicadores econômicos, sociais e fiscais

Exportado em 20/10/2026 a partir de uma conversa de levantamento e análise. Base para um novo projeto de dashboard virtual.

## Conteúdo

| Arquivo | O que traz |
|---|---|
| `dados.json` | Todas as tabelas num único arquivo, com descrição, colunas, legenda de tipos e fontes. Ponto de entrada recomendado para o dashboard. |
| `dados/*.csv` | As mesmas 15 tabelas, uma por arquivo (UTF-8, separador vírgula, decimal com ponto). |
| `fontes.csv` | Índice de fontes: `fonte_id`, descrição e URL (quando disponível). |
| `README.md` | Este arquivo: estrutura, ressalvas de método e roteiro sugerido para o dashboard. |

### Tabelas

1. `macro_pib_ipca_anual` — crescimento real do PIB e IPCA, 1995–2025
2. `indicadores_chave` — PIB, desemprego, IDH, expectativa de vida, mortalidade infantil, pobreza (IBGE)
3. `renda_pobreza_desigualdade_ipea` — renda, Gini e pobreza 1995 × 2024 (Ipea)
4. `educacao` — analfabetismo, escolaridade, Ideb, Pisa, investimento
5. `salario_minimo_cestas_sp` — salário mínimo e cestas básicas por salário, ano a ano, 1995–2026
6. `carne_kg_por_salario` — quilos de carne por salário (pontos disponíveis)
7. `itens_cesta_destaques` — custo da cesta, peso da carne, variações recentes de itens
8. `gasolina_energia_por_salario` — litros de gasolina e kWh por salário
9. `energia_tarifa_notas` — tarifas residenciais (duas séries de bases distintas)
10. `carga_tributaria_paises` — carga tributária % do PIB, Brasil × Europa, EUA e emergentes
11. `carga_tributaria_brasil_composicao` — composição da carga brasileira e estrutura OCDE
12. `contas_publicas_anual` — resultado primário do governo central e dívida bruta, 2010–2026
13. `contas_publicas_destaques` — déficits, juros, dívida bruta/líquida, conceito FMI
14. `despesas_por_funcao` — gasto por função (COFOG) e defesa (SIPRI)
15. `defesa_e_programas_sociais` — pessoal militar, LOA 2025, Bolsa Família, BPC

## Coluna `tipo` — grau de confiança de cada valor

- **oficial**: valor publicado pela fonte indicada.
- **calculo**: conta própria a partir de dados da fonte (ex.: salário ÷ custo da cesta).
- **estimativa**: estimativa de imprensa ou terceiros, não de série oficial.
- **serie_historica**: valor de série oficial (IBGE, Tesouro, BC) conhecido, mas **não reconferido ponto a ponto** nesta conversa. Recomenda-se validar no SIDRA/IBGE, no Tesouro Transparente e no SGS/BCB antes de publicação formal.

No dashboard, vale sinalizar visualmente `calculo` e `estimativa` (ex.: tom mais claro ou marcador vazado).

## Ressalvas de método

- **Séries de domicílios**: PNAD até 2015 e PNAD Contínua depois; comparações longas são indicativas.
- **IDH**: o valor de 1990 (0,590) segue metodologia anterior; comparação com 2023 é só indicativa.
- **Pobreza**: linhas do Ipea (US$ 3 e US$ 8,30/dia, PPC 2021) diferem das do IBGE. Ambos os critérios estão nos dados.
- **Cesta básica**: referência é São Paulo (em geral a mais cara). 1995–2016, 2020 e 2024 são médias anuais; os demais anos são meses de referência; **2019 sem dado localizado** (deixar lacuna, não interpolar).
- **Carne**: não há série pública anual contínua acessada. Picanha (IEA-SP) cobre 2007–2024; carne de primeira tem só dois pontos (estimativas). O corte muda muito o resultado.
- **Gasolina e energia**: sem série confiável antes de 2002. Tarifas de energia divergem conforme a fonte (ano-base e bandeiras).
- **Carga tributária**: 32,40% (Tesouro, 2025) × 33,7% (OCDE, 2024) — metodologias diferentes. Dados OCDE de 2024 são preliminares; Argentina (2023) e África do Sul (2022) têm anos anteriores.
- **Contas públicas**: o resultado primário refere-se ao governo central; o COFOG cobre as três esferas. Revisões do PIB podem alterar casas decimais.
- **Dívida bruta**: conceito do Banco Central; no conceito FMI (inclui títulos na carteira do BC) os valores são maiores (93,4% em dez/2025).

## Roteiro sugerido para o dashboard

1. **Visão geral** — cartões de KPI (PIB, IPCA, desemprego, IDH, expectativa de vida) + linhas de PIB e IPCA 1995–2025 com faixas das quatro fases do período (1995–2002 estabilização; 2003–2014 crescimento com inclusão; 2015–2021 crises; 2021–2025 retomada).
2. **Social** — comparações 1995 × 2024 de renda, Gini e pobreza; educação (analfabetismo, Ideb, Pisa) com recortes regional, racial e etário.
3. **Poder de compra** — barras ano a ano de cestas por salário; carne, leite, gasolina e energia; destaque "carne = 1/3 da cesta".
4. **Tributação** — ranking horizontal de carga tributária por país, Brasil em destaque; composição consumo × renda.
5. **Contas públicas** — barras de resultado primário, linha de dívida bruta até jul/2026, decomposição juros × déficit, gasto por função com comparação internacional.
6. **Fontes e método** — página com `fontes.csv` e as ressalvas acima.

Filtros úteis: período, tipo de dado (oficial/cálculo/estimativa) e tema.

## Artefatos já produzidos na conversa

Os infográficos ilustrados (indicadores gerais, salário × cesta, trajetória ano a ano e versão unificada) estão publicados num mesmo canvas de design no Claude e podem servir de referência visual.
