import re
from pathlib import Path

PADRAO_MERCOSUL = re.compile(r"^[A-Z]{3}[0-9][A-Z][0-9]{2}$")
PADRAO_ANTIGO = re.compile(r"^[A-Z]{3}[0-9]{4}$")
PALAVRAS_RUIDO = {"BRASIL", "MERCOSUL", "BR", "MERCO", "RASIL", "SIL"}


def limpar(texto):
    return " ".join(texto.split())


def tokens(texto):
    blocos = [b for b in re.split(r"[^A-Z0-9]+", texto.upper()) if b]
    encontrados = [(b, False) for b in blocos if 5 <= len(b) <= 8]
    # O EasyOCR pode devolver a placa separada, como "GG 70Z".
    for i in range(len(blocos) - 1):
        for j in range(i + 1, min(i + 4, len(blocos))):
            juncao = "".join(blocos[i : j + 1])
            if 5 <= len(juncao) <= 8:
                encontrados.append((juncao, True))
    return encontrados


def _nota_token(token, eh_juncao):
    # Heurística: formato de placa válido vale 100; ruído derruba a nota.
    if token in PALAVRAS_RUIDO:
        return -1.0
    if PADRAO_MERCOSUL.fullmatch(token) or PADRAO_ANTIGO.fullmatch(token):
        return 100.0

    nota = 50.0 - abs(7 - len(token)) * 4.0
    digitos = sum(c.isdigit() for c in token)
    if digitos == 0 or digitos == len(token):
        nota -= 20.0
    if token.startswith("BR") or token.endswith("BR"):
        nota -= 15.0
    if any(ruido in token for ruido in ("BRASI", "RASI", "MERC", "SIL")):
        nota -= 30.0
    if eh_juncao:
        nota -= 8.0
    return nota


def pontuar(texto):
    notas = [_nota_token(token, juncao) for token, juncao in tokens(texto)]
    return max(notas, default=0.0)


def extrair_placa(texto):
    melhor_token, melhor_nota = "", -1.0
    for token, juncao in tokens(texto):
        nota = _nota_token(token, juncao)
        if nota > melhor_nota:
            melhor_token, melhor_nota = token, nota
    return melhor_token if melhor_nota >= 0 else ""


def escrever_resultado(caminho, registros):
    linhas = []
    for nome, texto, placa in registros:
        linhas.append(f"{nome}: {placa or '(nenhum texto detectado)'}")
        linhas.append(f"    bruto: {texto.strip() or '(vazio)'}")
    Path(caminho).write_text("\n".join(linhas) + "\n", encoding="utf-8")
