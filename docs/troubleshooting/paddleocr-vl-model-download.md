# PaddleOCR-VL: Model Download Failure & Garbled Output

**Date:** 2026-08-06  
**Status:** Open

---

## Symptom

Model loads and runs (0.86s load, 2.77s inference on M4), but output is garbled:

```
Input:  Terminal screenshot with English + Russian text
Output: केa  คn  คn Gjit with  อn  店n  คn方式 with  器
```

---

## Root Cause

**The HuggingFace model was never actually downloaded.** The Swift CLI's built-in downloader shows progress (`10/10 files (100%)`) but writes nothing to the HF cache. The cache is completely empty:

```
$ find ~/.cache/huggingface/hub/models--PaddlePaddle--PaddleOCR-VL -type f
(empty)
```

The model runs with whatever small config/tokenizer files were downloaded (or embedded defaults), producing garbled output from an uninitialized or partially-initialized model.

### Secondary: `hf` CLI also fails

```
$ hf download PaddlePaddle/PaddleOCR-VL --local-dir /tmp/paddleocr-vl-model
FileNotFoundError: [Errno 2] No such file or directory:
  '/private/tmp/paddleocr-vl-model/.cache/huggingface/download/...incomplete'
```

The `huggingface-cli` is deprecated and replaced by `hf`, but `hf download` crashes with incomplete temp file errors.

---

## Diagnosis

### Step 1 — Verify cache

```bash
find ~/.cache/huggingface/hub/models--PaddlePaddle--PaddleOCR-VL -type f
# Empty — no model files

ls ~/.cache/huggingface/hub/models--PaddlePaddle--PaddleOCR-VL/blobs/
# Empty — no blobs

cat ~/.cache/huggingface/hub/models--PaddlePaddle--PaddleOCR-VL/refs/main
# No such file
```

### Step 2 — Check what the CLI downloads

The `Resolving HuggingFace model...` step completes quickly (sub-second) — it downloads only `config.json`, `tokenizer.json`, and other small metadata files, not the multi-GB `model.safetensors` weights.

### Step 3 — Verify model API

```bash
curl -sL "https://huggingface.co/api/models/PaddlePaddle/PaddleOCR-VL" | \
  python3 -c "import json,sys; d=json.load(sys.stdin); \
  [print(s['rfilename'], s['size']/1e9) for s in d['siblings'] if s['size']>1e6]"
# Shows 24 files including large safetensors files
```

The repository is valid and accessible. The download is failing client-side.

### Step 4 — Test alternative downloaders

| Tool | Result |
|------|--------|
| Swift CLI built-in | Reports success, writes nothing |
| `hf download` | Crashes with FileNotFoundError |
| `huggingface-cli download` | Deprecated, doesn't work |
| Python `huggingface_hub` | Not installed |
| Browser download | Works (manual) |

---

## Workaround (Manual)

### Option 1: Python huggingface_hub

```bash
pip install huggingface_hub
```

```python
from huggingface_hub import snapshot_download
snapshot_download(
    "PaddlePaddle/PaddleOCR-VL",
    local_dir="/tmp/paddleocr-vl-model",
    local_dir_use_symlinks=False,
)
```

Then point the CLI at the local model:

```bash
paddleocr-vl ocr image.png --model /tmp/paddleocr-vl-model
```

### Option 2: Git LFS

```bash
git clone https://huggingface.co/PaddlePaddle/PaddleOCR-VL /tmp/paddleocr-vl-model
```

### Option 3: Browser download

Download individual files from https://huggingface.co/PaddlePaddle/PaddleOCR-VL/tree/main

---

## Root Cause Investigation Needed

The Swift CLI's download code needs inspection. Likely issues:

1. **LFS support** — Model weights are stored via Git LFS on HF; the downloader may not resolve LFS pointers
2. **Auth** — Some HF models require authentication even for public repos
3. **Download path** — The CLI may download to a temp location that gets cleaned up before the files are moved to cache
4. **Permission** — The CLI may lack write permissions to `~/.cache/huggingface/`

### Next Steps

1. Enable verbose/network logging in the Swift downloader
2. Test with `hf_xet` (HuggingFace's new transfer protocol) vs standard HTTP
3. Try with `HF_HUB_ENABLE_HF_TRANSFER=1`
4. Check if the model requires `HF_TOKEN` even for public access

---

## References

- [HuggingFace Hub Python Library](https://huggingface.co/docs/huggingface_hub)
- [hf_xet transfer protocol](https://huggingface.co/docs/huggingface_hub/guides/download#faster-downloads)
- [PaddleOCR-VL Model Card](https://huggingface.co/PaddlePaddle/PaddleOCR-VL)
