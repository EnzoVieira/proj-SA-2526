#!/bin/bash
set -e

REMOTE=pi@raspberrypi.local
REMOTE_DIR=/home/pi/proj-SA-2526

echo "→ A sincronizar para $REMOTE..."
rsync -avz --delete \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '.git' \
  --exclude '.env' \
  --exclude 'logs' \
  --exclude '*.pyc' \
  --exclude 'assets/models' \
  --exclude 'assets/dataset.csv' \
  ./ "$REMOTE:$REMOTE_DIR/"

echo "→ Done."
