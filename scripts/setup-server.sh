#!/usr/bin/env bash
set -euo pipefail

sudo apt update && sudo apt upgrade -y

sudo apt install -y ca-certificates curl gnupg lsb-release nginx certbot python3-certbot-nginx openssl

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo systemctl enable docker
sudo systemctl start docker

sudo mkdir -p /opt/anunciacerto/backend/certbot/conf/live/api.anunciacerto.com.br
sudo mkdir -p /opt/anunciacerto/backend/certbot/www

if [ ! -f /opt/anunciacerto/backend/certbot/conf/live/api.anunciacerto.com.br/fullchain.pem ]; then
  sudo openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout /opt/anunciacerto/backend/certbot/conf/live/api.anunciacerto.com.br/privkey.pem \
    -out /opt/anunciacerto/backend/certbot/conf/live/api.anunciacerto.com.br/fullchain.pem \
    -subj "/CN=api.anunciacerto.com.br"
fi

echo "Servidor preparado. Proximo passo: copiar backend para /opt/anunciacerto/backend e rodar deploy-production.sh"
