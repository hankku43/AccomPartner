# 階段 1: 構建前端 Vue 應用程式
FROM node:18-alpine AS build

# 設定工作目錄
WORKDIR /app

# 複製依賴檔案
COPY package*.json ./

# 安裝依賴
RUN npm install

# 複製原始碼編譯 Vue
COPY . .
RUN npm run build

# 階段 2: 使用 Nginx 託管靜態網頁
FROM nginx:alpine

# 將預設的 Nginx 配置替換為支援前端路由 (History Mode) 及反向代理的版本
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 從第一階段複製編譯產生的靜態檔 (dist/ 目錄) 到 Nginx 特定目錄
COPY --from=build /app/dist /usr/share/nginx/html

# 對外開放 80 port
EXPOSE 80

# 啟動 Nginx 服務，固定在前台執行
CMD ["nginx", "-g", "daemon off;"]
