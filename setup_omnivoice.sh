#!/usr/bin/env bash
# Cài OmniVoice vào môi trường riêng venv-omnivoice (xem setup_omnivoice.bat)
set -e
cd "$(dirname "$0")"
python3 -m venv venv-omnivoice
if command -v nvidia-smi >/dev/null; then IDX=cu128; else IDX=cpu; fi
venv-omnivoice/bin/pip install torch torchaudio --index-url https://download.pytorch.org/whl/$IDX
venv-omnivoice/bin/pip install omnivoice soundfile
echo "Xong. Model mặc định: splendor1811/omnivoice-vietnamese"
