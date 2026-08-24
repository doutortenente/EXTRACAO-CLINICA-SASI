# EXTRACAO-CLINICA-SASI

Motor clínico local para transformar JSON bruto extraído de folhas da UTI em texto copiável e flags separadas.

## Escopo atual

- Soma determinística de ganhos, diurese, drenos, resíduo gástrico e ultrafiltração.
- Máximo, mínimo e contagem de limites dos sinais vitais.
- Conferência entre células e totais manuscritos sem confiar no total da folha.
- Rejeição de séries vazias, identificadores duplicados/injetados e estruturas incompatíveis com o contrato clínico.
- Formatação clínica conforme `BRIEFING.md` auditado.
- Interface de terminal, OCR local e serviço HTTP restrito ao próprio computador.
- Imagens e PDFs escaneados passam por Tesseract local; nenhum documento é enviado à rede.

## Fora do escopo

- Não é frontend, banco, prontuário ou cópia do SASI-V3.
- Não grava no Supabase.
- Não contém serviço de OCR em nuvem nem credenciais.
- OCR transforma arquivo em texto bruto; a revisão humana e a estruturação em JSON continuam obrigatórias.

## Uso

```bash
PYTHONPATH=src python3 scripts/extract_ocr.py folha.png --output texto-extraido.json
PYTHONPATH=src python3 -m extracao_clinica_sasi.cli --file examples/leito-sintetico.json
PYTHONPATH=src python3 -m extracao_clinica_sasi.server --host 127.0.0.1 --port 8765
```

Rotas locais:

- `GET /healthz`
- `POST /v1/compile` com `Content-Type: application/json`

## Verificação

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
```

## Regra clínica

Dado ausente ou ilegível permanece ausente. O modelo extrai células; Python calcula. Flags e divergências ficam fora do bloco copiável.
