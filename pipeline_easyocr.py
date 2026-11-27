from pathlib import Path

import easyocr

from src import segmentacao
from src.ocr_utils import escrever_resultado, extrair_placa, limpar, pontuar
from src.preprocessamento import variantes

RAIZ = Path(__file__).resolve().parent
PASTA_IMAGENS = RAIZ / "data" / "placas"
PASTA_RECORTES = RAIZ / "resultados" / "placas_recortadas"
ARQUIVO_SAIDA = RAIZ / "resultados" / "easyocr.txt"


def main():
    reader = easyocr.Reader(["pt", "en"], gpu=False, verbose=False)

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
            bruto = limpar(" ".join(reader.readtext(imagem_variante, detail=0)))
            if bruto:
                tentativas.append((pontuar(bruto), bruto, nome_variante))

        if tentativas:
            tentativas.sort(reverse=True)
            _, bruto, variante = tentativas[0]
            print(f"{imagem.name:14s} [{variante}] {extrair_placa(bruto)}")
        else:
            bruto = ""
        registros.append((imagem.name, bruto, extrair_placa(bruto)))

    escrever_resultado(ARQUIVO_SAIDA, registros)
    print(f"\nResultados salvos em: {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    main()
