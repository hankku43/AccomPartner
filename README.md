# AccomPartner — AI 鋼琴伴奏生成系統

> **即時感受 AI 帶來的音樂靈感**  
> 輸入一段旋律，AccomPartner 在幾秒內為你生成完整的鋼琴伴奏，支援即時鍵盤演奏、MIDI 匯入與多軌樂譜顯示。

---

## 系統特色

| 功能 | 說明 |
|------|------|
| 🎹 **即時伴奏（Realtime Piano）** | 使用 `@huggingface/transformers` 在瀏覽器端進行 ONNX 推理，零後端延遲 |
| 🎼 **旋律編輯器（Melody Editor）** | Grid Pad 與 VexFlow 五線譜雙模式，呼叫後端 One-Stage Transformer 生成伴奏 |
| 🎵 **進階模式（Advanced Mode）** | 上傳 MIDI 選軌，呼叫後端 One/Two-Stage Transformer，支援弦標音與多小節樂譜顯示 |
| 🔒 **安全設計** | Rate limiting（5 req/min）、MIDI 上傳 10MB 限制、CORS 白名單 |
| 🐳 **容器化部署** | Docker Compose 一鍵啟動前後端，Nginx 反向代理 |

---

## 專案結構

```
AccomPartner/
├── backend/                    # FastAPI 後端
│   ├── app/
│   │   ├── main.py             # 應用程式入口（lifespan, CORS, rate limiter）
│   │   ├── core/
│   │   │   ├── config.py       # Pydantic Settings 環境變數管理
│   │   │   ├── cleanup.py      # 暫存 MIDI 檔定時清理任務
│   │   │   └── limiter.py      # SlowAPI rate limiter
│   │   ├── routers/
│   │   │   └── generate.py     # /api/generate-from-json, /api/generate-from-midi
│   │   ├── controllers/
│   │   │   └── generate_controller.py
│   │   ├── services/
│   │   │   ├── oneStage_service.py     # One-Stage AR Transformer 推理
│   │   │   ├── twoStage_service.py     # Two-Stage Transformer 推理（含和弦預測）
│   │   │   ├── oneStage_transformer.py
│   │   │   ├── twoStage_transformer.py
│   │   │   └── twoStage_chord_transformer.py
│   │   └── models/
│   │       └── schemas.py      # Pydantic 請求/回應 Schema
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/                   # Vue 3 + Vite 前端
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.js
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── HeroSection.vue     # 粒子動畫首頁
│   │   │   │   └── Navigation.vue      # 模式切換導覽列
│   │   │   └── modes/
│   │   │       ├── RealtimePiano.vue   # 即時鋼琴（瀏覽器端 ONNX 推理）
│   │   │       ├── MelodyEditor.vue    # 旋律編輯器（後端推理）
│   │   │       └── AdvancedMode.vue    # MIDI 上傳進階模式
│   │   ├── composables/
│   │   │   └── useAppState.js          # 全域狀態（Pinia）
│   │   └── services/
│   │       ├── aiService.js            # HuggingFace Transformers.js ONNX 推理（RealtimePiano 專用）
│   │       ├── audioService.js         # Tone.js 音訊引擎（鋼琴、鼓組取樣器）
│   │       └── tokenizerService.js     # MIDI tokenization / detokenization
│   ├── nginx.conf                      # 生產環境 Nginx 配置
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml          # 生產環境
├── docker-compose.dev.yml      # 開發環境（Vite HMR）
└── THIRD_PARTY_LICENSES.md
```

---

## 快速開始

### 方法一：Docker（推薦）

```bash
# 開發模式（含 Vite HMR）
docker-compose -f docker-compose.dev.yml up --build

# 生產模式
docker-compose up --build
```

前端：`http://localhost:5173`（開發）/ `http://localhost:80`（生產）  
後端 API 文件：`http://localhost:8000/docs`

### 方法二：本機手動啟動

#### 後端

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# 編輯 .env，設定 MODEL_DIR 等環境變數

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端

```bash
cd frontend
npm install
npm run dev
```

---

## 環境變數

複製 `backend/.env.example` 為 `backend/.env`，主要設定項：

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `MODEL_DIR` | *(必填)* | 模型權重 `.pt` 檔案所在目錄 |
| `ALLOWED_ORIGINS` | `http://localhost:5173,...` | CORS 白名單，多個以逗號分隔 |
| `RATE_LIMIT` | `10` | API 每分鐘請求上限 |
| `DEFAULT_BPM` | `120` | 預設 BPM |

---

## 模型架構

| 模式 | 架構 | 用途 |
|------|------|------|
| `oneStage` | One-Stage AR Transformer | 直接從旋律 tokens 生成伴奏 |
| `twoStage-std` | Two-Stage Transformer（標準） | Stage 1 預測和弦，Stage 2 生成伴奏 |
| `twoStage-bar` | Two-Stage Transformer（小節） | 以小節為單位的 Two-Stage |
| `twoStage-nar` | Two-Stage NAR Transformer | 非自迴歸（Non-Autoregressive）生成 |

**即時模式（RealtimePiano）** 使用量化 ONNX 模型在瀏覽器中推理（`@huggingface/transformers`），不會呼叫後端 API。

---

## API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| `GET` | `/api/health` | 健康檢查 |
| `POST` | `/api/generate-from-json` | 從 JSON 旋律生成伴奏（回傳 MIDI binary） |
| `POST` | `/api/generate-from-midi` | 上傳 MIDI 檔生成伴奏（回傳 JSON `{ midi_b64, chords }`） |

詳細 Schema 請見 `/docs`（Swagger UI）。

---

## 技術棧

**後端**  
Python 3.10 · FastAPI · Pydantic v2 · PyTorch · MidiTok · Symusic · Music21 · SlowAPI · Uvicorn

**前端**  
Vue 3 · Vite · Tone.js · VexFlow · @huggingface/transformers · Pinia

**部署**  
Docker · Docker Compose · Nginx

---

## License

本專案以 **MIT License** 授權開放。  
模型訓練資料使用 **POP909 Dataset**，僅限非商業及學術研究用途。  
詳細第三方套件授權請參閱 [`THIRD_PARTY_LICENSES.md`](./THIRD_PARTY_LICENSES.md)。
