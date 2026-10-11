"""Uso:
  python -m coletor raw                      # todos os conjuntos
  python -m coletor raw votacoes deputados   # só alguns
  python -m coletor raw --forcar             # recarrega mesmo sem mudança
"""
import argparse
import logging
import sys

from . import raw
from .db import conectar


def main() -> int:
    p = argparse.ArgumentParser(prog="coletor")
    sub = p.add_subparsers(dest="etapa", required=True)
    r = sub.add_parser("raw", help="baixa os arquivos da Câmara para a camada raw")
    r.add_argument("conjuntos", nargs="*", help="ex.: votacoes votacoesVotos referencias")
    r.add_argument("--forcar", action="store_true")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with conectar() as con:
        con.autocommit = True  # cada arquivo controla a própria transação
        falhas = raw.executar(con, set(args.conjuntos) or None, args.forcar)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
