@echo off
REM Cài OmniVoice (tiếng Việt, module dự phòng) vào MÔI TRƯỜNG RIÊNG venv-omnivoice
REM (omnivoice cần transformers>=5.3, xung đột với qwen-tts nên không cài chung venv chính)
cd /d %~dp0
python -m venv venv-omnivoice
call venv-omnivoice\Scripts\activate
nvidia-smi >nul 2>&1
if not errorlevel 1 (
  pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
) else (
  pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
)
pip install omnivoice soundfile
echo.
echo Xong. Model mac dinh: splendor1811/omnivoice-vietnamese (tu tai lan dau).
echo Muon dung G-OmniVoice: dang nhap HuggingFace, chap nhan dieu khoan o
echo   https://huggingface.co/g-group-ai-lab/g-omnivoice  roi dat bien:
echo   set HF_TOKEN=... ^& set SHORTS_OMNI_MODEL=g-group-ai-lab/g-omnivoice
call deactivate
