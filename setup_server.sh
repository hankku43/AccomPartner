#!/bin/bash
# =========================================================================
# setup_server.sh
# -------------------------------------------------------------------------
# AWS EC2 t4g.small (Ubuntu ARM) 專用自動化初始設定腳本。
# 職責：
# 1. 自動檢測與安裝 Docker (含 docker-compose)
# 2. 自動切分 8GB 虛擬記憶體 (Swap)，以防止 PyTorch 載入模型時 OOM 崩潰。
# 
# 使用方式 (在登入 EC2 伺服器後)：
# chmod +x setup_server.sh && ./setup_server.sh
# =========================================================================

set -e # 若指令失敗立刻停止腳本

echo "========================================="
echo "🧰 AccomPartner 伺服器初始化腳本啟動..."
echo "========================================="

# =====================================================
# 1. 建立並掛載 8GB Swap 虛擬記憶體
# =====================================================
echo "\n[1/3] 開始建立 8GB Swap 虛擬記憶體..."
if [ -f /swapfile ]; then
    echo "⚠️ Swap 檔案已存在，跳過建立。"
else
    # 建立 8G 空白檔案
    sudo fallocate -l 8G /swapfile
    # 設定權限 (基於安全性)
    sudo chmod 600 /swapfile
    # 將檔案格式化為 Swap
    sudo mkswap /swapfile
    # 啟用 Swap
    sudo swapon /swapfile

    # 加入 fstab (確保重開機自動掛載)
    sudo cp /etc/fstab /etc/fstab.bak
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

    # 調降 swappiness，讓系統除非必要不要隨便用 swap，同時又不至於讓 OOM killer 發動
    sudo sysctl vm.swappiness=10
    echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf

    echo "✅ 8GB Swap 虛擬記憶體掛載成功！"
fi

# =====================================================
# 2. 安裝 Docker 與 Docker Compose
# =====================================================
echo "\n[2/3] 開始安裝 Docker..."
if command -v docker >/dev/null 2>&1; then
    echo "⚠️ Docker 已由系統安裝，跳過此步驟。"
else
    # 設定存儲庫
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl gnupg lsb-release

    # 加入 Docker 官方的 GPG 金鑰
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc

    # 設定穩定的存儲庫
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # 正式安裝 Docker 等元件
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # 確保開機啟動
    sudo systemctl enable docker
    sudo systemctl start docker
    echo "✅ Docker 安裝完成！"
fi

# =====================================================
# 3. 權限設定
# =====================================================
echo "\n[3/3] 設定 docker 指令權限 (免 sudo)..."
if id -nG "${USER}" | grep -qw "docker"; then
    echo "⚠️ 使用者已在 docker 群組中。"
else
    sudo usermod -aG docker "${USER}"
    echo "✅ 成功將 ${USER} 加入 docker 群組。"
fi

echo "========================================="
echo "🎉 初始化設定全數完成！"
echo "========================================="
echo "⚠️  極度重要：為了讓 Docker 權限生效，請您輸入以下指令（或者登出再重新登入 SSH）："
echo "    newgrp docker"
echo "👉  設定完成後，您就可以在專案目錄下執行 'docker compose up -d --build' 來啟動您的網站了！"
