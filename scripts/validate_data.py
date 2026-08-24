#!/usr/bin/env python3
"""Valida o JSON clínico executando o mesmo contrato usado em produção."""

import argparse
import json

from extracao_clinica_sasi.core import compilar_payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("arquivo")
    args = parser.parse_args()
    try:
        with open(args.arquivo, encoding="utf-8") as handle:
            resultado = compilar_payload(json.load(handle))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(
        json.dumps(
            {
                "valid": True,
                "requires_human_review": resultado["requires_human_review"],
                "flags_taticos": resultado["flags_taticos"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if resultado["requires_human_review"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
