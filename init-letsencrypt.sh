#!/bin/bash

if ! [ -x "$(command -v docker-compose)" ] && ! [ -x "$(command -v docker)" ]; then
  echo 'Error: docker is not installed.' >&2
  exit 1
fi

domains=(accompartner.dev www.accompartner.dev)
rsa_key_size=4096
data_path="./certbot"
email="admin@accompartner.dev" # 適當填入或略過

echo "### 正在檢查是否存在舊的憑證..."
if [ -d "$data_path" ]; then
  read -p "已經存在舊的憑證目錄，是否要覆蓋重新簽發？ (y/N) " decision
  if [ "$decision" != "Y" ] && [ "$decision" != "y" ]; then
    exit
  fi
  sudo rm -rf "$data_path"
fi

echo "### 為網域建立臨時的 RSA Let's Encrypt 憑證..."
path="/etc/letsencrypt/live/$domains"
mkdir -p "$data_path/conf/live/$domains"
docker compose run --rm --entrypoint "\
  openssl req -x509 -nodes -newkey rsa:$rsa_key_size -days 1 \
    -keyout '$path/privkey.pem' \
    -out '$path/fullchain.pem' \
    -subj '/CN=localhost'" certbot

echo "### 啟動 Nginx..."
docker compose up --force-recreate -d frontend

echo "### 刪除剛剛生成的臨時憑證..."
docker compose run --rm --entrypoint "\
  rm -Rf /etc/letsencrypt/live/$domains && \
  rm -Rf /etc/letsencrypt/archive/$domains && \
  rm -Rf /etc/letsencrypt/renewal/$domains.conf" certbot

echo "### 請求真正的 Let's Encrypt 憑證..."
domain_args=""
for domain in "${domains[@]}"; do
  domain_args="$domain_args -d $domain"
done

# 如果有註冊信箱，可以改為 --email $email (取消 --register-unsafely-without-email)
docker compose run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    $domain_args \
    --email $email \
    --rsa-key-size $rsa_key_size \
    --agree-tos \
    --no-eff-email \
    --force-renewal" certbot

echo "### 重新載入 Nginx 配置..."
docker compose exec frontend nginx -s reload

echo "✅ SSL 憑證已成功申請並套用！"
