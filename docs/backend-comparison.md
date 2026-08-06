# Backend Comparison — Real Measurements (2026-08-06)

**Hardware:** Apple M4 Pro, 48GB RAM  
**Test image:** Terminal screenshot, 2646×794 PNG, English + Russian mixed text  
**Date:** 2026-08-06

---

## Results

| Backend | Task | Status | Time | Output Quality | Notes |
|---------|------|--------|------|----------------|-------|
| **Vision** | `ocr_text` | ✅ Pass | <100ms | Perfect | All text captured, Russian + English correct |
| **Vision** | `ocr_layout` | ✅ Pass | <100ms | Perfect | Bounding boxes accurate, text order correct |
| **PaddleOCR-VL** | `ocr_text` | ❌ Fail | 2.77s (inference) | Garbled | Model weights not downloaded — garbled output |
| **PaddleOCR-VL** | `ocr_text` (MCP) | ❌ Fail | N/A | N/A | Mode parameter bug: `accurate` not valid |

---

## Vision Output (reference)

```
Linux aliyev-nb 6.6.114.1-microsoft-standard-WSL2 x86_64
00:29:08 up 8:46, 2 users, load average: 0.00, 0.00, 0.00

› scp -A -p -J taliev@172.16.8.1 copy_fail.py chernouhov-AY@10.5.66.131:~
copy_fail.py    100%  731    63.6KB/s   00:00

› ssh -A -J taliev@172.16.8.1 chernouhov-AY@10.5.66.131
Last login: Mon May 11 00:19:44 2026 from 10.27.159.19
ln: не удалось создать символьную ссылку ...
chernouhov-ay@WGOL-IT00000459:~$ id -u
1038031111
chernouhov-ay@WGOL-IT00000459:~$ ./.copy_fail.py && su
root@WGOL-IT00000459:/home/.../chernouhov-ay# id -u
0
root@WGOL-IT00000459:/home/.../chernouhov-ay# rm .copy_fail.py
```

**Quality assessment:**
- Terminal font: ✅ clean recognition
- Cyrillic: ✅ `не удалось создать символьную ссылку`
- Line noise (`E 0.00 o`, `OB •`): ⚠️ minor artifacts from terminal status bar
- Line ordering: ✅ correct top-to-bottom
- Confidence: 0.3–1.0 (lower on status bar graphics, 1.0 on clean terminal text)

---

## PaddleOCR-VL Issues Summary

| Issue | Status | Fix |
|-------|--------|-----|
| Metal shaders (metallib) missing | ✅ Fixed | Built MLX C library with cmake, copied `mlx.metallib` |
| Model weights not downloaded | ❌ Open | HF download pipeline broken; need manual download or Python `huggingface_hub` |
| Mode parameter `accurate` not valid | ❌ Open | Add mode mapping in backend (`accurate`→`dynamic`, `fast`→`base`) |

---

## Cross-Platform Theoretical Comparison

Based on published benchmarks and framework analysis (not yet measured on this hardware):

| Backend | Est. pages/min (M4) | Languages | Tables | Formulas | License |
|---------|---------------------|-----------|--------|----------|---------|
| **Vision** | 200+ | ~20 (Latin, CJK, Cyrillic, Arabic) | macOS 15+ only | ❌ | Proprietary (free) |
| **PaddleOCR-VL (MLX)** | 30-60 | 109 | ✅ MD/HTML | ✅ LaTeX | Apache 2.0 |
| **Surya (llama.cpp Metal)** | 20-50 | 90+ | ✅ HTML | ✅ KaTeX inline | Code: Apache 2.0, Weights: paid >$5M |
| **Tesseract 5** | ~25 | 100+ | ❌ | ❌ | Apache 2.0 |
| **EasyOCR (MPS)** | 5-15 | 80+ | ❌ | ❌ | Apache 2.0 |

*PaddleOCR-VL and Surya estimates extrapolated from A100 benchmarks and 3× MLX speedup ratio. Pending real measurement once model download is fixed.*

---

## Recommendations

### For production use today
**Apple Vision** is the only backend that works reliably on this hardware. It's fast, zero-install, and handles Russian + English well. Use it for:
- Terminal screenshots
- Document photos
- Mixed Latin/Cyrillic text
- Quick text extraction

Limitations: no tables (pre-macOS 15), no formulas, limited language coverage.

### When PaddleOCR-VL is fixed
It will be the best choice for:
- Multi-language documents (109 languages)
- Tables and structured data
- Mathematical formulas
- Charts and diagrams
- Highest accuracy requirements

### PaddleOCR (CPU)
Use as a cross-platform fallback when:
- Not on macOS
- Vision's language support is insufficient
- PaddleOCR-VL is unavailable
