# Final Project: Music Generation System (音樂生成系統)

A full-stack music generation system featuring a Transformer-based accompaniment model, a FastAPI backend, and a Vue.js frontend.

這是一個全方位的音樂生成系統，包含基於 Transformer 的伴奏模型、FastAPI 後端以及 Vue.js 前端介面。

---

## English Version

### Project Structure
- **`backend/`**: FastAPI-based server providing API endpoints for music generation and processing.
- **`frontend/`**: Vue.js application providing a modern web interface for users to interact with the models.
- **`model/`**: Core logic for various music generation models (Transformer, NAR, etc.), including training and inference scripts.
- **`data/`**: Data processing scripts and storage (Dataset files are excluded from Git to save space).

### Getting Started

#### Backend Setup
1. Navigate to the `backend/` directory.
2. Create a virtual environment: `python -m venv venv`
3. Activate the environment and install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and configure as needed.
5. Run the server: `uvicorn app.main:app --reload`

#### Frontend Setup
1. Navigate to the `frontend/` directory.
2. Install dependencies: `npm install`
3. Start the development server: `npm run dev`

### Deployment & Version Control
- This project uses a root `.gitignore` to exclude large model weights and local environment files.
- Model weights should be stored locally in `model/**/checkpoints/` or tracked using Git LFS if necessary.

---

## 繁體中文版本 (Traditional Chinese)

### 專案結構
- **`backend/`**: 基於 FastAPI 的伺服器，提供音樂生成與處理的 API 接口。
- **`frontend/`**: Vue.js 應用程式，提供現代化的網頁介面供使用者與模型互動。
- **`model/`**: 各類音樂生成模型（Transformer、NAR 等）的核心邏輯，包含訓練與推理腳本。
- **`data/`**: 資料處理腳本與儲存空間（資料集檔案已從 Git 排除以節省空間）。

### 入門指南

#### 後端設定 (Backend)
1. 進入 `backend/` 目錄。
2. 建立虛擬環境：`python -m venv venv`
3. 啟動環境並安裝依賴：`pip install -r requirements.txt`
4. 將 `.env.example` 複製為 `.env` 並根據需求進行配置。
5. 啟動伺服器：`uvicorn app.main:app --reload`

#### 前端設定 (Frontend)
1. 進入 `frontend/` 目錄。
2. 安裝依賴：`npm install`
3. 啟動開發伺服器：`npm run dev`

### 部署與版本控制
- 本專案使用根目錄下的 `.gitignore` 來排除大型模型權重與本地環境檔案。
- 模型權重應儲存在本地的 `model/**/checkpoints/` 中，或視需要使用 Git LFS 進行追蹤。

---

## License (授權)

This project is for educational/research purposes. (Add your license here, e.g., MIT).
本專案僅供教育與研究使用。（請在此處添加您的授權條款，例如 MIT）。
