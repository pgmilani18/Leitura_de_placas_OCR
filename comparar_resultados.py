from pathlib import Path

RAIZ = Path(__file__).resolve().parent
RESULTADOS = RAIZ / "resultados"


def linhas_de_placa(caminho):
    dados = {}
    for linha in Path(caminho).read_text(encoding="utf-8").splitlines():
        if ":" in linha and not linha.startswith(" "):
            nome, valor = linha.split(":", 1)
            dados[nome.strip()] = valor.strip()
    return dados


def main():
    tesseract = linhas_de_placa(RESULTADOS / "tesseract.txt")
    easyocr = linhas_de_placa(RESULTADOS / "easyocr.txt")

    linhas = ["Comparação Tesseract x EasyOCR", "=" * 40]
    for nome in sorted(set(tesseract) | set(easyocr)):
        linhas.append(
            f"{nome:14s} | Tesseract: {tesseract.get(nome, '-'):12s} "
            f"| EasyOCR: {easyocr.get(nome, '-')}"
        )

    destino = RESULTADOS / "comparativo.txt"
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"Comparação salva em: {destino}")


if __name__ == "__main__":
    main()
