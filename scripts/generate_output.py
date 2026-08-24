#!/usr/bin/env python3
"""Gera texto clínico limpo; flags seguem em arquivo separado ou stderr."""

import argparse
import json
import sys

from extracao_clinica_sasi.core import compilar_payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("arquivo")
    parser.add_argument("--flags-output")
    args = parser.parse_args()
    try:
        with open(args.arquivo, encoding="utf-8") as handle:
            resultado = compilar_payload(json.load(handle))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(resultado["texto_clinico"])
    flags = json.dumps(resultado["flags_taticos"], ensure_ascii=False, indent=2)
    if args.flags_output:
        with open(args.flags_output, "w", encoding="utf-8") as handle:
            handle.write(flags + "\n")
    elif resultado["flags_taticos"]:
        print(flags, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
