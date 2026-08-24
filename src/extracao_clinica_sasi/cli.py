"""Interface de terminal do motor clínico."""

from __future__ import annotations

import argparse
import json
import sys

from .core import compilar_payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Compila JSON clínico SASI sem aritmética por IA")
    parser.add_argument("--file", help="arquivo JSON; sem este argumento, lê stdin")
    args = parser.parse_args()
    try:
        if args.file:
            with open(args.file, encoding="utf-8") as handle:
                payload = json.load(handle)
        else:
            payload = json.load(sys.stdin)
        print(json.dumps(compilar_payload(payload), ensure_ascii=False, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
