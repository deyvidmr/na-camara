"""Uso:
  python -m ia relevancia                 # classifica candidatos ainda não avaliados
  python -m ia relevancia --limite 10     # só os 10 primeiros (para testar)
  python -m ia relevancia --simular       # testa o fluxo sem chamar a API
  python -m ia relevancia --refazer       # reavalia tudo com a versão atual do prompt
"""
import argparse
import logging
import sys

from . import relevancia


def main() -> int:
    p = argparse.ArgumentParser(prog="ia")
    sub = p.add_subparsers(dest="tarefa", required=True)
    r = sub.add_parser("relevancia", help="relevância de cada projeto para cada tema do cidadão")
    r.add_argument("--limite", type=int)
    r.add_argument("--refazer", action="store_true")
    r.add_argument("--simular", action="store_true")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # o SDK registra cada requisição HTTP em INFO; deixa só avisos
    logging.getLogger("httpx2").setLevel(logging.WARNING)
    falhas = relevancia.executar(args.refazer, args.limite, args.simular)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
