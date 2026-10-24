#!/usr/bin/env bash
# Prepares a fresh Ubuntu 24.04 server (e.g. AWS Lightsail) to run the bot. Safe to re-run.
#
# Either paste this file into Lightsail's "launch script" box when creating the instance,
# or run it over SSH:  curl -fsSL <raw URL of this file> | sudo bash
#
# It installs Docker, adds swap, clones the repo to /opt/psek-bot, and schedules a nightly
# database backup. It starts the bot only once /opt/psek-bot/.env exists, so on a first run
# copy your .env there afterwards and start it as the last lines printed say.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/phakawatfong/psek-bot.git}"
APP_DIR="${APP_DIR:-/opt/psek-bot}"
APP_USER="${APP_USER:-ubuntu}"
SWAP_SIZE="${SWAP_SIZE:-1G}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root (sudo bash setup.sh)." >&2
  exit 1
fi

echo "==> Swap ($SWAP_SIZE): building the image can need more memory than the smallest plans have"
if ! swapon --show=NAME --noheadings | grep -qx /swapfile; then
  fallocate -l "$SWAP_SIZE" /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
fi
grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab

echo "==> Docker, from Docker's own apt repository (Ubuntu's package lacks the compose plugin)"
if ! command -v docker >/dev/null || ! docker compose version >/dev/null 2>&1; then
  apt-get update
  apt-get install -y ca-certificates curl git
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  # shellcheck disable=SC1091  # /etc/os-release exists on every Ubuntu
  codename="$(. /etc/os-release && echo "$VERSION_CODENAME")"
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc]" \
    "https://download.docker.com/linux/ubuntu $codename stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin \
    docker-compose-plugin
fi
systemctl enable --now docker # so the bot comes back after a reboot
usermod -aG docker "$APP_USER"

echo "==> Code in $APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
  sudo -u "$APP_USER" git -C "$APP_DIR" pull --ff-only
else
  install -d -o "$APP_USER" -g "$APP_USER" "$APP_DIR"
  sudo -u "$APP_USER" git clone "$REPO_URL" "$APP_DIR"
fi

echo "==> Nightly backup at 03:00 UTC into the bot-data volume (keeps 14 days)"
install -m 0644 -o "$APP_USER" -g "$APP_USER" /dev/null /var/log/psek-bot-backup.log
cat > /etc/cron.d/psek-bot-backup <<EOF
0 3 * * * $APP_USER cd $APP_DIR && docker compose run --rm bot backup >> /var/log/psek-bot-backup.log 2>&1
EOF

if [ -f "$APP_DIR/.env" ]; then
  echo "==> Starting the bot"
  cd "$APP_DIR"
  docker compose up -d --build
  docker compose ps
else
  cat <<EOF

==> Almost done. From your own computer, copy your .env to the server:
      scp .env $APP_USER@<server-ip>:$APP_DIR/.env
    then on the server:
      chmod 600 $APP_DIR/.env
      cd $APP_DIR && docker compose up -d --build
EOF
fi
