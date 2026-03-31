# AI 伴奏生成實驗室 — FastAPI 後端

## 架構說明（MVC）

```
app/
├── core/           # 共用設定與工具（Rate Limiter、環境變數）
├── models/         # Pydantic 資料模型（輸入驗證 / 回傳格式）
├── services/       # 業務服務層（MIDI 轉換、模型推理）
├── controllers/    # 控制器（協調 service 呼叫，處理例外）
└── routers/        # 路由定義（HTTP 介面，Rate Limit 裝飾器）
```

## 快速啟動

### 1. 建立虛擬環境並安裝依賴

```bash
cd "c:\GithubView\final project\backend"
python -m venv venv
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
copy .env.example .env
# 編輯 .env，填入模型路徑
```

### 3. 啟動開發伺服器

```bash
uvicorn app.main:app --reload --port 8000
```

伺服器啟動後可訪問：
- **API 文件（Swagger UI）**：http://127.0.0.1:8000/docs
- **健康檢查**：http://127.0.0.1:8000/api/health

## API 端點

| 方法 | 路徑 | 說明 | 限速 |
|------|------|------|------|
| GET  | `/api/health` | 健康檢查 | 無 |
| POST | `/api/generate-from-json` | 從 JSON 旋律生成伴奏 | 5次/min/IP |
| POST | `/api/generate-from-midi` | 從 MIDI 上傳生成伴奏 | 5次/min/IP |

## 整合 AI 模型（AR / NAR）

目前為 **MOCK 模式**，直接回傳旋律本身作為測試用 MIDI。

要啟用真實推理：
1. 在 `.env` 中設定 `AR_SCRIPT_PATH` 或 `NAR_SCRIPT_PATH`
2. 取消 `app/services/ar_service.py` 或 `nar_service.py` 中的 subprocess 呼叫區塊
3. 確認推理腳本支援以下介面：
   ```
   python generate.py --input <midi_in> --output <midi_out> --model_dir <dir>
   ```

## 新增推理模式

只需在 `app/services/model_router.py` 的 `_SERVICE_MAP` 加入新條目：

```python
from app.services import new_model_service

_SERVICE_MAP = {
    "ar": ar_service.generate,
    "nar": nar_service.generate,
    "new_mode": new_model_service.generate,  # ← 加這行
}
```
