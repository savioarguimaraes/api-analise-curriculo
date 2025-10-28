# Imagem base Python 3.12 slim
FROM python:3.12-slim

# Definir diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema necessárias para EasyOCR e OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copiar arquivo de dependências
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Pré-baixar modelos do EasyOCR durante o build (evita download no startup)
# Isso adiciona ~500MB à imagem mas reduz startup de 10-20min para ~10s
RUN python -c "import easyocr; print('Baixando modelos do EasyOCR...'); reader = easyocr.Reader(['pt', 'en'], gpu=False, verbose=True); print('Modelos baixados com sucesso!')"

# Copiar código da aplicação
COPY main.py .
COPY langgraph.json .
COPY src/ ./src/

# Expor porta da aplicação
EXPOSE 8000

# Health check (start-period aumentado para dar tempo do EasyOCR carregar modelos)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Comando para iniciar a aplicação
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
