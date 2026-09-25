"""Tiến trình phụ chạy OmniVoice trong MÔI TRƯỜNG PYTHON RIÊNG (venv-omnivoice).

Lý do: omnivoice cần transformers>=5.3, còn qwen-tts cần transformers==4.57.3 → không cài chung được.
App gửi từng yêu cầu dạng JSON 1 dòng qua stdin, worker giữ model trong bộ nhớ và trả JSON 1 dòng qua stdout.
Chạy tay để thử:  venv-omnivoice/Scripts/python studio/omni_worker.py
"""
import json
import os
import sys


def main() -> None:
    import soundfile as sf
    import torch
    from omnivoice import OmniVoice

    name = os.environ.get("SHORTS_OMNI_MODEL", "splendor1811/omnivoice-vietnamese")
    cuda = torch.cuda.is_available() and not os.environ.get("SHORTS_NO_GPU")
    model = OmniVoice.from_pretrained(name, device_map="cuda:0" if cuda else "cpu",
                                      dtype=torch.float16 if cuda else torch.float32)
    print(json.dumps({"ready": True, "device": "cuda" if cuda else "cpu", "model": name}), flush=True)
    for line in sys.stdin:
        if not line.strip():
            continue
        job = json.loads(line)
        try:
            kw = {"text": job["text"], "ref_audio": job["ref_audio"], "ref_text": job["ref_text"]}
            audio = model.generate(**kw)
            if isinstance(audio, (list, tuple)):
                audio = audio[0]
            if hasattr(audio, "detach"):
                audio = audio.detach().float().cpu().numpy()
            audio = audio.reshape(-1)
            sr = int(getattr(model, "sampling_rate", 0) or getattr(model, "sample_rate", 0) or 24000)
            sf.write(job["out"], audio, sr)
            print(json.dumps({"id": job.get("id"), "ok": True, "seconds": len(audio) / sr}), flush=True)
        except Exception as e:  # noqa: BLE001
            print(json.dumps({"id": job.get("id"), "ok": False, "error": repr(e)}), flush=True)


if __name__ == "__main__":
    main()
