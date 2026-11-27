# Extração e OCR de placas veiculares

Pipeline para **detectar, recortar e reconhecer placas** do dataset em `data/placas`,
comparando **Tesseract OCR** e **EasyOCR** sobre exatamente as mesmas imagens recortadas.

## Estrutura

```
.
├── data/placas/                 # dataset (24 imagens)
├── src/
│   ├── segmentacao.py           # localização e recorte da placa
│   ├── preprocessamento.py      # ampliação, CLAHE e limiarização
│   ├── ocr_utils.py             # limpeza, pontuação e escrita dos resultados
│   └── __init__.py
├── pipeline_tesseract.py        # pipeline completo com Tesseract
├── pipeline_easyocr.py          # pipeline completo com EasyOCR
├── comparar_resultados.py       # gera o comparativo final
├── resultados/
│   ├── placas_recortadas/       # placas extraídas (.png)
│   ├── tesseract.txt            # texto reconhecido pelo Tesseract
│   ├── easyocr.txt              # texto reconhecido pelo EasyOCR
│   └── comparativo.txt          # lado a lado das duas abordagens
├── requirements.txt
└── .gitignore
```

## Instalação

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Além dos pacotes Python, foi necessário instalar o **binário do Tesseract**:

- Windows: `winget install --id UB-Mannheim.TesseractOCR`
- Linux (Ubuntu/Debian): `sudo apt install -y tesseract-ocr tesseract-ocr-por`
- Inclua o idioma português (`por.traineddata`) na pasta `tessdata` quando necessário.
- Se o Tesseract estiver em outro caminho, ajuste `localizar_tesseract()` em
  `pipeline_tesseract.py`.

O EasyOCR baixa os modelos (`craft_mlt_25k`, `latin_g2`) na primeira execução.

## Execução

```bash
python pipeline_tesseract.py
python pipeline_easyocr.py
python comparar_resultados.py
```

Cada pipeline: localiza a placa, salva o recorte em `resultados/placas_recortadas/`,
testa três pré-processamentos, escolhe a leitura mais plausível e grava o `.txt`.

## Relatório do Projeto

### 1. Objetivo

Construir um pipeline de visão computacional que, a partir das imagens do dataset,
**(a)** encontre a placa, **(b)** extraia apenas essa região e **(c)** submeta o mesmo
recorte a dois mecanismos diferentes de OCR — Tesseract e EasyOCR — para comparar o
texto reconhecido. O foco do exercício é entender as etapas de processamento e as
diferenças entre as ferramentas, não apenas obter a placa correta.

### 2. Etapa de segmentação e extração (`src/segmentacao.py`)

A localização é feita em duas camadas:

1. **Detector de texto:** o EasyOCR, por meio do modelo CRAFT, devolve caixas
   delimitadoras para as regiões de texto da imagem. Isso evita escrever um detector
   de placas do zero e funciona bem mesmo quando a placa ocupa poucos pixels.
2. **Filtro geométrico em OpenCV:** cada caixa passa por regras simples:
   - proporção largura/altura entre **2,2 e 8,5** (a faixa de caracteres da placa é
     sempre bem alongada);
   - largura mínima de **12% da imagem** e altura mínima de **2%**;
   - a caixa não pode começar nos **15% superiores** da imagem, para descartar
     letreiros, placas de loja ou textos no céu;
   - entre as candidatas restantes, escolhe-se a de maior área.

Em seguida, a caixa da faixa de texto é **ampliada**: ~12% à esquerda (para incluir a
bandeira), ~6% à direita e ~30% acima/abaixo (para incluir a faixa azul com
“BRASIL”). O resultado é salvo como PNG em `resultados/placas_recortadas/`, com o
mesmo nome da imagem original.

> Observação de implementação: a leitura usa `np.fromfile` + `cv2.imdecode` em vez de
> `cv2.imread`, porque o caminho do projeto contém o caractere acentuado `í` e o
> OpenCV do Windows não abre esses caminhos diretamente.

### 3. Etapa de pré-processamento (`src/preprocessamento.py`)

Cada recorte é replicado em três versões, conforme a orientação de testar técnicas
diferentes:

| Variante | O que faz | Por que testar |
|---|---|---|
| `ampliado` | redimensiona 3× com interpolação cúbica | caracteres pequenos ficam maiores e mais legíveis |
| `clahe` | converte para cinza e aplica CLAHE (contraste local) | recupera texto em imagens com luz desigual |
| `otsu` | aplica limiar binário global de Otsu | separa tinta escura do fundo claro da placa |

Os pipelines não escolhem uma variante “de cara”: eles rodam o OCR nas três e deixam
a etapa de pontuação decidir qual leitura é mais plausível para aquela imagem.

### 4. Etapa de OCR

**Pipeline Tesseract** (`pipeline_tesseract.py`)

- binário localizado automaticamente com `shutil.which("tesseract")` (funciona no
  Windows e no Linux);
- `lang="por"`;
- whitelist `ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789`, já que a placa só tem letras e
  números;
- `psm 7` (linha única de texto) e `psm 11` (texto esparso) — o dataset tem desde
  placas bem enquadradas até placas com reflexos e caracteres espalhados;
- para cada combinação de variante × `psm`, o texto é limpo e pontuado.

**Pipeline EasyOCR** (`pipeline_easyocr.py`)

- `Reader(["pt", "en"], gpu=False)` — execução em CPU, sem depender de CUDA;
- `reader.readtext(imagem, detail=0)` retorna apenas os textos, sem caixas;
- mesma política de testar as três variantes e pontuar o resultado.

Como os dois pipelines leem os PNGs já recortados, a comparação é feita **sobre o
mesmo input de imagem**; a diferença observada vem do motor de OCR e do pré-processamento
que cada um selecionou.

### 5. Pós-processamento e pontuação (`src/ocr_utils.py`)

O texto bruto dos OCRs costuma vir com ruído: `BRASIL`, `BR`, `MERCOSUL`, quebras de
linha e caracteres soltos. A limpeza:

- colapsa espaços/quebras em uma única linha (`limpar`);
- extrai blocos alfanuméricos de 5 a 8 caracteres, inclusive junções de blocos curtos
  vizinhos (o EasyOCR às vezes devolve `GG 70Z` em vez de `GG70Z`);
- descarta palavras conhecidas como ruído;
- atribui nota maior quando o token bate com um dos formatos:
  - Mercosul: `AAA0A00` (3 letras, 1 dígito, 1 letra, 2 dígitos);
  - antigo: `AAA-0000`;
  - caso contrário, penaliza tokens muito curtos/longos, sem dígitos ou sem letras,
    além de junções e trechos que contêm `BRASI`, `RASI`, `MERC` ou `SIL`.

O token com maior nota vira a “placa” exibida. O texto original fica disponível na
linha `bruto:` de cada `.txt`, para conferência.

### 6. Resultados obtidos

Arquivos gerados: `resultados/tesseract.txt`, `resultados/easyocr.txt` e
`resultados/comparativo.txt`.

#### 6.1 Resultados do Tesseract

| Imagem | Texto reconhecido |
|---|---|
| 1 - Copia.JPG | IFA1T95 |
| 1.JPG | IFA1T95 |
| 10 - Copia.JPG | PBU7Z7 |
| 10.JPG | PBU7Z7 |
| 11 - Copia.JPG | LMNL3U9S |
| 11.JPG | LMNL3U9S |
| 12.JPG | JET7G88 |
| 13.JPG | 3P890S9 |
| 14.JPG | PHISHOO |
| 15.JPG | THY7E39 |
| 16.JPG | UHK5055 |
| 17.JPG | NZ0SM77 |
| 18.JPG | (nenhum texto detectado) |
| 19.JPG | V4PVJQA |
| 2.JPG | 2ZQQPVX |
| 20 - Copia.JPG | FQM2151 |
| 20.JPG | FQM2151 |
| 3.JPG | Z22168 |
| 4.JPG | QOWON47 |
| 5.JPG | EEQ3F44 |
| 6.JPG | 5AIAOSI |
| 7.JPG | V37EWJE |
| 8.JPG | XHY6U2 |
| 9.JPG | ROA4JI6 |

#### 6.2 Resultados do EasyOCR

| Imagem | Texto reconhecido |
|---|---|
| 1 - Copia.JPG | IFA1T95 |
| 1.JPG | IFA1T95 |
| 10 - Copia.JPG | PPU7522 |
| 10.JPG | PPU7522 |
| 11 - Copia.JPG | MNL3U98 |
| 11.JPG | MNL3U98 |
| 12.JPG | JET7G88 |
| 13.JPG | ABP8085 |
| 14.JPG | PHI8HTN |
| 15.JPG | THY7EI9 |
| 16.JPG | UXK5055 |
| 17.JPG | NZE3M77 |
| 18.JPG | XDASES0 |
| 19.JPG | ES142 |
| 2.JPG | NEVID8 |
| 20 - Copia.JPG | J9UJL |
| 20.JPG | J9UJL |
| 3.JPG | MER9C55 |
| 4.JPG | UR0ND7 |
| 5.JPG | A1BRY9S |
| 6.JPG | 7YL3X75 |
| 7.JPG | EXQ2195 |
| 8.JPG | XHY6U29 |
| 9.JPG | A0A4J16 |

#### 6.3 Relação entre os resultados

| Imagem | Tesseract | EasyOCR |
|---|---|---|
| 1 - Copia.JPG | IFA1T95 | IFA1T95 |
| 1.JPG | IFA1T95 | IFA1T95 |
| 10 - Copia.JPG | PBU7Z7 | PPU7522 |
| 10.JPG | PBU7Z7 | PPU7522 |
| 11 - Copia.JPG | LMNL3U9S | MNL3U98 |
| 11.JPG | LMNL3U9S | MNL3U98 |
| 12.JPG | JET7G88 | JET7G88 |
| 13.JPG | 3P890S9 | ABP8085 |
| 14.JPG | PHISHOO | PHI8HTN |
| 15.JPG | THY7E39 | THY7EI9 |
| 16.JPG | UHK5055 | UXK5055 |
| 17.JPG | NZ0SM77 | NZE3M77 |
| 18.JPG | (nenhum texto detectado) | XDASES0 |
| 19.JPG | V4PVJQA | ES142 |
| 2.JPG | 2ZQQPVX | NEVID8 |
| 20 - Copia.JPG | FQM2151 | J9UJL |
| 20.JPG | FQM2151 | J9UJL |
| 3.JPG | Z22168 | MER9C55 |
| 4.JPG | QOWON47 | UR0ND7 |
| 5.JPG | EEQ3F44 | A1BRY9S |
| 6.JPG | 5AIAOSI | 7YL3X75 |
| 7.JPG | V37EWJE | EXQ2195 |
| 8.JPG | XHY6U2 | XHY6U29 |
| 9.JPG | ROA4JI6 | A0A4J16 |

### 7. Análise da comparação

- **EasyOCR** foi mais consistente nas imagens de boa iluminação e pouco reflexo.
  Exemplos claros: `1.JPG`, `11.JPG`, `12.JPG`, `16.JPG`, `17.JPG` e `8.JPG`, em que
  a leitura bate com o padrão Mercosul de 7 caracteres. Por outro lado, seu texto
  bruto praticamente sempre traz `BRASIL`, `BR` ou `MERCOSUL`, o que exige a etapa de
  filtragem descrita acima.
- **Tesseract** funcionou bem quando o recorte ficou limpo (ex.: `1.JPG` → `IFA1T95`,
  `4.JPG` → `QOWON47`, `9.JPG` → `ROA4JI6`), mas foi mais sensível a brilho, reflexo e
  inclinação. Em `18.JPG` nenhuma das tentativas gerou um token confiável. Confusões
  típicas apareceram em `0/O`, `1/I` e `5/S`.
- As quatro imagens `- Copia.JPG` são duplicatas exatas de `1.JPG`, `10.JPG`, `11.JPG`
  e `20.JPG`, respectivamente; como esperado, reproduzem os mesmos resultados.
- As tabelas registram **o que cada motor reconheceu** em cada imagem. A heurística de
  pontuação apenas escolhe, entre as leituras do próprio OCR, aquela com formato mais
  plausível de placa.
