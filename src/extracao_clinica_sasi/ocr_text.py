"""Extração local de texto e OCR; nenhum documento sai da máquina."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

TEXT_TYPES = {".md", ".txt", ".csv"}
IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}


def _executar(comando: list[str], timeout: int = 120) -> str:
    processo = subprocess.run(
        comando,
        capture_output=True,
        check=False,
        text=True,
        timeout=timeout,
    )
    if processo.returncode != 0:
        raise RuntimeError(processo.stderr.strip() or f"falha ao executar {comando[0]}")
    return processo.stdout


def _ocr_imagem(path: Path) -> str:
    executavel = shutil.which("tesseract")
    if not executavel:
        raise RuntimeError("tesseract não está instalado")
    idioma = os.environ.get("SASI_OCR_LANG", "por+eng")
    try:
        return _executar([executavel, str(path), "stdout", "-l", idioma, "--psm", "6"])
    except RuntimeError:
        if idioma == "eng":
            raise
        return _executar([executavel, str(path), "stdout", "-l", "eng", "--psm", "6"])


def _texto_pdf(path: Path) -> tuple[str, str]:
    pdftotext = shutil.which("pdftotext")
    if pdftotext:
        texto = _executar([pdftotext, "-layout", str(path), "-"])
        if texto.strip():
            return texto, "camada-textual-pdf"
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise RuntimeError("PDF sem texto legível e pdftoppm não está instalado para OCR")
    with tempfile.TemporaryDirectory(prefix="sasi-ocr-") as directory:
        prefixo = Path(directory) / "pagina"
        _executar([pdftoppm, "-png", "-r", "200", str(path), str(prefixo)], timeout=300)
        paginas = sorted(Path(directory).glob("pagina-*.png"))
        if not paginas:
            raise RuntimeError("PDF não gerou páginas para OCR")
        textos = [_ocr_imagem(pagina).strip() for pagina in paginas]
    return "\n\n".join(textos) + "\n", "tesseract-local-pdf"


def extrair_texto(path: str | Path) -> dict[str, Any]:
    arquivo = Path(path)
    if not arquivo.is_file():
        raise ValueError(f"arquivo não encontrado: {arquivo}")
    extensao = arquivo.suffix.lower()
    if extensao in TEXT_TYPES:
        texto = arquivo.read_text(encoding="utf-8")
        metodo = "texto-original"
    elif extensao in IMAGE_TYPES:
        texto = _ocr_imagem(arquivo)
        metodo = "tesseract-local"
    elif extensao == ".pdf":
        texto, metodo = _texto_pdf(arquivo)
    else:
        raise ValueError(f"tipo não suportado: {extensao or '[sem extensão]'}")
    warnings: list[str] = []
    if not texto.strip():
        warnings.append("nenhum texto legível extraído")
    return {
        "source_file": arquivo.name,
        "texto": texto,
        "metodo": metodo,
        "warnings": warnings,
    }
