"""Baixa as séries das APIs abertas e salva retratos em data/, para o painel não depender delas.

    python scripts/atualizar_dados_abertos.py

Grava (o que conseguir baixar):
- data/banco_mundial.csv  Banco Mundial, aba Mundo
- data/fmi_divida.csv     FMI, dívida e resultado fiscal por país
- data/ipca_itens.csv     IBGE/SIDRA, IPCA anual por item
- data/bcb_divida.csv     Banco Central, dívida bruta e líquida mensais

Com um retrato presente, o painel usa ele em vez da API. Rode de novo para atualizar; apague o arquivo
para voltar à consulta ao vivo.
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from painel import banco_mundial as bm  # noqa: E402
from painel import fontes_abertas as fa  # noqa: E402


def salva(nome, funcao, arquivo):
    try:
        tabela = funcao()
        if isinstance(tabela, tuple):
            tabela, falhas = tabela
            if falhas:
                print(f"  {nome}: sem resposta para {', '.join(falhas)}")
        if tabela.empty:
            raise ValueError("nenhum dado")
        tabela.to_csv(arquivo, index=False)
        print(f"{nome}: {len(tabela)} linhas em {arquivo}")
        return True
    except Exception as erro:
        print(f"{nome}: falhou ({erro})")
        return False


def main() -> int:
    ano = date.today().year
    resultados = [
        salva("Banco Mundial", lambda: bm.baixa_tudo(ano), bm.ARQUIVO),
        salva("FMI", lambda: fa.baixa_fmi(ultimo_ano_observado=ano - 1), fa.FMI_ARQUIVO),
        salva("IBGE/SIDRA", lambda: fa.baixa_sidra(ano_final=ano - 1), fa.SIDRA_ARQUIVO),
        salva("Banco Central", fa.baixa_sgs, fa.SGS_ARQUIVO),
    ]
    return 0 if any(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
