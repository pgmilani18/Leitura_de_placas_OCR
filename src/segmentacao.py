from pathlib import Path

import cv2
import numpy as np

EXTENSOES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def listar_imagens(pasta):
    pasta = Path(pasta)
    return sorted(p for p in pasta.iterdir() if p.suffix.lower() in EXTENSOES)


def _caixas_texto(resultados, largura, altura):
    candidatas = []
    for caixa, texto, confianca in resultados:
        xs = [ponto[0] for ponto in caixa]
        ys = [ponto[1] for ponto in caixa]
        x1, x2 = int(min(xs)), int(max(xs))
        y1, y2 = int(min(ys)), int(max(ys))
        larg, alt = x2 - x1, y2 - y1
        proporcao = larg / max(alt, 1)

        # A faixa de caracteres da placa é horizontal e bem alongada.
        if not (2.2 <= proporcao <= 8.5):
            continue
        if larg < 0.12 * largura or alt < 0.02 * altura:
            continue
        if y1 < 0.15 * altura:  # ignora letreiros no topo
            continue

        candidatas.append((larg * alt, x1, y1, x2, y2, texto, confianca))
    return sorted(candidatas, reverse=True)


def segmentar_imagem(caminho, reader):
    # imdecode aceita caminhos com acentos; cv2.imread falha no Windows.
    dados = np.fromfile(str(caminho), dtype=np.uint8)
    imagem = cv2.imdecode(dados, cv2.IMREAD_COLOR)
    if imagem is None:
        return None
    altura, largura = imagem.shape[:2]

    resultados = reader.readtext(imagem, detail=1)
    candidatas = _caixas_texto(resultados, largura, altura)
    if not candidatas:
        return None

    _, x1, y1, x2, y2, texto, confianca = candidatas[0]
    larg, alt = x2 - x1, y2 - y1

    # Amplia a caixa para incluir a bandeira e a faixa azul "BRASIL".
    x1 = max(0, x1 - int(0.12 * larg))
    x2 = min(largura, x2 + int(0.06 * larg))
    y1 = max(0, y1 - int(0.30 * alt))
    y2 = min(altura, y2 + int(0.30 * alt))

    recorte = imagem[y1:y2, x1:x2]
    return recorte, (x1, y1, x2, y2), texto, confianca


def salvar_recorte(recorte, caminho):
    sucesso, dados = cv2.imencode(".png", recorte)
    if sucesso:
        dados.tofile(str(caminho))
