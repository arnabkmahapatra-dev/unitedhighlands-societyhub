#!/usr/bin/env bash
# ============================================================================
# One-command provisioning + deploy of SocietyHub to Google Cloud e2-micro.
#
# PREREQUISITES (you must do these once — they need YOUR Google login):
#   1. Have a Google Cloud account with BILLING enabled on a project.
#   2. gcloud CLI installed (brew install --cask google-cloud-sdk).
#   3. Authenticate + select project:
#        gcloud auth login
#        gcloud config set project YOUR_PROJECT_ID
#
# THEN just run:   bash deploy/gcp-provision.sh
#
# Optional overrides (env vars):
#   VM_NAME   (default: unitedhighlands-societyhub)
#   ZONE      (default: us-west1-b  — an Always-Free US zone)
#   DOMAIN    (e.g. unitedhighlands-societyhub.duckdns.org for auto-HTTPS)
# ============================================================================
set -euo pipefail

VM_NAME="${VM_NAME:-unitedhighlands-societyhub}"
ZONE="${ZONE:-us-west1-b}"
MACHINE="${MACHINE:-e2-micro}"
IMAGE_FAMILY="ubuntu-2204-lts"
IMAGE_PROJECT="ubuntu-os-cloud"
DISK_SIZE="30GB"
DOMAIN="${DOMAIN:-}"

# Move to repo root (this script lives in deploy/)
cd "$(dirname "$0")/.."

command -v gcloud >/dev/null || {
  echo "ERROR: gcloud CLI not found. Install: brew install --cask google-cloud-sdk"
  exit 1
}

PROJECT="$(gcloud config get-value project 2>/dev/null || true)"
if [ -z "$PROJECT" ] || [ "$PROJECT" = "(unset)" ]; then
  echo "ERROR: No project set. Run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi
echo "==> Project: $PROJECT   VM: $VM_NAME   Zone: $ZONE"

# --- Ensure a local backend/.env with a strong SECRET_KEY ---
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
fi
if grep -q "change-me-to-a-long-random-secret" backend/.env; then
  NEWKEY="$(openssl rand -hex 32)"
  # portable in-place sed (macOS + Linux)
  sed -i.bak "s/^SECRET_KEY=.*/SECRET_KEY=${NEWKEY}/" backend/.env && rm -f backend/.env.bak
  echo "==> Generated a fresh SECRET_KEY in backend/.env"
fi

echo "==> Enabling Compute Engine API (first time can take a minute)"
gcloud services enable compute.googleapis.com

echo "==> Creating firewall rules for HTTP/HTTPS"
gcloud compute firewall-rules create societyhub-http \
  --allow tcp:80 --target-tags=http-server --quiet 2>/dev/null || true
gcloud compute firewall-rules create societyhub-https \
  --allow tcp:443 --target-tags=https-server --quiet 2>/dev/null || true

echo "==> Creating the e2-micro VM (skipped if it already exists)"
gcloud compute instances create "$VM_NAME" \
  --zone="$ZONE" \
  --machine-type="$MACHINE" \
  --image-family="$IMAGE_FAMILY" \
  --image-project="$IMAGE_PROJECT" \
  --boot-disk-size="$DISK_SIZE" \
  --boot-disk-type=pd-standard \
  --tags=http-server,https-server --quiet 2>/dev/null \
  || echo "   (VM already exists — continuing)"

echo "==> Waiting for SSH to become available"
for i in $(seq 1 30); do
  if gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="echo ok" --quiet >/dev/null 2>&1; then
    break
  fi
  sleep 6
done

echo "==> Packaging the app"
TAR="$(mktemp -t societyhub-XXXX).tar.gz"
tar --exclude='backend/.venv' \
    --exclude='*__pycache__*' \
    --exclude='*.pyc' \
    --exclude='*.db' \
    --exclude='.git' \
    -czf "$TAR" backend deploy docker-compose.yml

echo "==> Uploading to the VM"
gcloud compute scp --zone="$ZONE" "$TAR" "$VM_NAME":~/societyhub.tar.gz --quiet

echo "==> Installing Docker + starting the app on the VM"
REMOTE_CMD="set -e
mkdir -p ~/SocietyHub
tar -xzf ~/societyhub.tar.gz -C ~/SocietyHub
cd ~/SocietyHub
if ! command -v docker >/dev/null; then bash deploy/gcp-setup.sh; fi
export DOMAIN='${DOMAIN}'
sudo -E docker compose up -d --build"
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="$REMOTE_CMD"

IP="$(gcloud compute instances describe "$VM_NAME" --zone="$ZONE" \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)')"

echo
echo "============================================================"
echo " SocietyHub is deployed!"
if [ -n "$DOMAIN" ]; then
  echo "   URL : https://${DOMAIN}   (Caddy is fetching the certificate)"
  echo "   Make sure ${DOMAIN} points to ${IP} in your DNS/DuckDNS."
else
  echo "   URL : http://${IP}/"
  echo "   (For a name + HTTPS, set DOMAIN and re-run — see deploy notes.)"
fi
echo "   Login: IT Support mobile/password from backend/.env"
echo "============================================================"
