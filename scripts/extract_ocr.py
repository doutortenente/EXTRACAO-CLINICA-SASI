#!/usr/bin/env python3
"""Extrai a camada de texto de PDF OCR, Markdown ou TXT sem enviar dados à nuvem."""

import argparse
import json

from extracao_clinica_sasi.ocr_text import extrair_texto


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("arquivo")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        resultado = extrair_texto(args.arquivo)
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    conteudo = json.dumps(resultado, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(conteudo + "\n")
    else:
        print(conteudo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
