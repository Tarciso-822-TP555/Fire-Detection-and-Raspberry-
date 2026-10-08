FROM ultralytics/ultralytics:8.3.204-arm64

WORKDIR /app

# Instala pacotes extras necessários
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências adicionais do Python
RUN pip install --no-cache-dir \
    flask \
    prometheus-client \
    opencv-python-headless \
    "numpy<2" \
    onnxruntime

# Copia os arquivos do projeto
COPY . .

EXPOSE 8000 8001

CMD ["python3", "detect.py"]
