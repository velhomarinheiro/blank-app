"""Baixa os indicadores do Banco Mundial e salva um retrato em data/banco_mundial.csv.

Com o retrato salvo, a aba Mundo abre sem depender da API. Rode de novo para atualizar:

    python scripts/atualizar_banco_mundial.py
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from painel import banco_mundial as bm  # noqa: E402


def main() -> int:
    tabela, falhas = bm.baixa_tudo(date.today().year)
    if tabela.empty:
        print("Nenhum dado baixado. Verifique a conexão com api.worldbank.org.")
        return 1
    tabela.sort_values(["indicador", "iso3", "ano"]).to_csv(bm.ARQUIVO, index=False)
    print(f"{len(tabela)} linhas salvas em {bm.ARQUIVO}")
    if falhas:
        print("Indicadores que falharam:", ", ".join(falhas))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
