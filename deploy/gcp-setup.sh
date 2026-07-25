#!/usr/bin/env bash
# One-time setup for a fresh Ubuntu VM on Google Cloud e2-micro (Always Free).
# Installs Docker + Compose plugin. Run on the VM:  bash deploy/gcp-setup.sh
set -euo pipefail

echo "==> Updating packages"
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg

echo "==> Installing Docker Engine + Compose plugin"
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg |
	sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
	"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" |
	sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "==> Allowing current user to run docker without sudo"
sudo usermod -aG docker "$USER" || true

echo
echo "Docker installed. Log out and back in (or run 'newgrp docker'), then:"
echo "  cd ~/SocietyHub"
echo "  cp backend/.env.example backend/.env   # then edit secrets"
echo "  export DOMAIN=unitedhighlands-societyhub.duckdns.org   # or leave unset for HTTP"
echo "  docker compose up -d --build"
