FROM python:3.10-slim

# 設定工作目錄
WORKDIR /app

# 設定環境變數：防止 Python 寫入 .pyc 檔案以及強制將輸出行標準化
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安裝系統依賴 (編譯 C++ 函式庫如 symusic 所需的工具)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴清單
COPY requirements.txt .

# 安裝 Python 依賴
# (在 ARM 架構下，pip 預設會下載相容於 aarch64 的 CPU 版本 PyTorch)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 複製應用內容 (注意: 部署時不應將模型權重包進 Image，應透過 volume 掛載，但此處為求無腦啟動先全部複製)
COPY . .

# 暴露 8000 port (僅供容器間通訊，不會直接對外)
EXPOSE 8000

# 啟動 FastAPI 服務
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
