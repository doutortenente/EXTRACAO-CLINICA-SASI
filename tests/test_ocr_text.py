import tempfile
import unittest
import shutil
from pathlib import Path

from extracao_clinica_sasi.ocr_text import extrair_texto

ROOT = Path(__file__).resolve().parents[1]


class OcrTextTests(unittest.TestCase):
    def test_ci_executa_ocr_real(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("tesseract-ocr", workflow)
        self.assertIn("Pillow", workflow)

    def test_le_markdown_ocr_sem_alterar_conteudo(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "folha.md"
            path.write_text("PAM 70\nDiurese 300 ml\n", encoding="utf-8")
            resultado = extrair_texto(path)
        self.assertEqual(resultado["texto"], "PAM 70\nDiurese 300 ml\n")
        self.assertEqual(resultado["warnings"], [])

    def test_rejeita_tipo_nao_suportado(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "folha.bin"
            path.write_bytes(b"x")
            with self.assertRaises(ValueError):
                extrair_texto(path)

    @unittest.skipUnless(shutil.which("tesseract"), "tesseract ausente")
    def test_faz_ocr_local_de_imagem(self):
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            self.skipTest("Pillow ausente")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "folha.png"
            image = Image.new("RGB", (900, 220), "white")
            draw = ImageDraw.Draw(image)
            font = ImageFont.truetype("DejaVuSans.ttf", 72)
            draw.text((30, 60), "SASI LEITO 01", fill="black", font=font)
            image.save(path)
            resultado = extrair_texto(path)
        self.assertIn("SASI", resultado["texto"].upper())
        self.assertEqual(resultado["metodo"], "tesseract-local")


if __name__ == "__main__":
    unittest.main()
