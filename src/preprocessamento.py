import cv2


def variantes(recorte):
    ampliado = cv2.resize(
        recorte, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC
    )
    cinza = cv2.cvtColor(ampliado, cv2.COLOR_BGR2GRAY)
    # CLAHE realça o contraste em imagens com luz desigual.
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(cinza)
    _, otsu = cv2.threshold(clahe, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return [
        ("ampliado", ampliado),
        ("clahe", clahe),
        ("otsu", otsu),
    ]
