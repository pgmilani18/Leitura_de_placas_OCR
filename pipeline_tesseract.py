import shutil
import sys
from pathlib import Path

import easyocr
import pytesseract

from src import segmentacao
from src.ocr_utils import escrever_resultado, extrair_placa, limpar, pontuar
from src.preprocessamento import variantes

RAIZ = Path(__file__).resolve().parent
PASTA_IMAGENS = RAIZ / "data" / "placas"
PASTA_RECORTES = RAIZ / "resultados" / "placas_recortadas"
ARQUIVO_SAIDA = RAIZ / "resultados" / "tesseract.txt"
CONFIG = (
    "--psm {psm} -c tessedit_char_whitelist="
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
)


def localizar_tesseract():
    encontrado = shutil.which("tesseract")
    if encontrado:
        return encontrado
    padrao = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if padrao.exists():
        return str(padrao)
    sys.exit(
        "Tesseract não encontrado. Instale o binário e/ou ajuste localizar_tesseract()."
    )


def main():
    pytesseract.pytesseract.tesseract_cmd = localizar_tesseract()
    reader = easyocr.Reader(["pt", "en"], gpu=False, verbose=False)  # só localiza

    PASTA_RECORTES.mkdir(parents=True, exist_ok=True)
    imagens = segmentacao.listar_imagens(PASTA_IMAGENS)
    registros = []

    for imagem in imagens:
        resultado = segmentacao.segmentar_imagem(imagem, reader)
        if resultado is None:
            print(f"[AVISO] placa não detectada: {imagem.name}")
            continue
        recorte, _, _, _ = resultado
        segmentacao.salvar_recorte(recorte, PASTA_RECORTES / f"{imagem.stem}.png")

        tentativas = []
        for nome_variante, imagem_variante in variantes(recorte):
            for psm in (7, 11):  # 7 = linha única; 11 = texto esparso
                bruto = pytesseract.image_to_string(
                    imagem_variante,
                    lang="por",
                    config=CONFIG.format(psm=psm),
                )
                bruto = limpar(bruto)
                if bruto:
                    tentativas.append((pontuar(bruto), bruto, nome_variante, psm))

        if tentativas:
            tentativas.sort(reverse=True)
            _, bruto, variante, psm = tentativas[0]
            print(f"{imagem.name:14s} [{variante}, psm {psm}] {extrair_placa(bruto)}")
        else:
            bruto = ""
        registros.append((imagem.name, bruto, extrair_placa(bruto)))

    escrever_resultado(ARQUIVO_SAIDA, registros)
    print(f"\nResultados salvos em: {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    main()
