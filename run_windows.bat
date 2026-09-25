@echo off
cd /d %~dp0
if not exist venv (
  python -m venv venv
  call venv\Scripts\activate
  pip install -r requirements.txt
  nvidia-smi >nul 2>&1
  if not errorlevel 1 (
    echo [GPU NVIDIA] Cai PyTorch CUDA de dung GPU...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
    pip install -r requirements-gpu.txt
  )
  python check_gpu.py
) else (
  call venv\Scripts\activate
)
python app.py
