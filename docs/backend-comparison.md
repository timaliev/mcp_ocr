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
| **Xiaomi-OCR-0** | `document`/`table` | ✅ Pass | 2–18s | Perfect on clean text | See 2026-11-03 measurements below |

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

## PaddleOCR-VL — removed (2026-11-03)

The backend was removed from this project. On Apple Silicon it required a hand-built
Swift/MLX CLI, hung for minutes on table requests (and on formula/chart by design),
loaded several GB per invocation, and produced poor Cyrillic — it never became usable.
Use **Xiaomi-OCR-0** for structured document output and **Vision** for fast text.
Historical notes are in the `docs/research/` report and in git history.

## Cross-Platform Theoretical Comparison

Based on published benchmarks and framework analysis (not yet measured on this hardware):

| Backend | Measured on this hardware | Languages | Tables | Formulas | License |
|---------|---------------------------|-----------|--------|----------|---------|
| **Vision** | <100 ms/page | ~30 locales (Latin, CJK, Cyrillic, Arabic) | ❌ no structure API | ❌ | Proprietary (free) |
| **Xiaomi-OCR-0** (MPS, fp16) | 2.4–18 s/page | RU/EN/DE/JA solid; AR/KO weak | ✅ OTSL→HTML | ✅ LaTeX | Apache 2.0 |
| **PaddleOCR-VL (MLX)** | removed — unusable | 109 claimed | ⚠️ | ⚠️ | Apache 2.0 |
| **Surya (llama.cpp Metal)** | 20–50 | 90+ | ✅ HTML | ✅ KaTeX inline | Code: Apache 2.0, Weights: paid >$5M |
| **Tesseract 5** | ~25 | 100+ | ❌ | ❌ | Apache 2.0 |
| **EasyOCR (MPS)** | 5–15 | 80+ | ❌ | ❌ | Apache 2.0 |

*Vision, Xiaomi and Paddle numbers are measured on this machine; Surya/Tesseract/EasyOCR
are estimates from published benchmarks.*

---

## 2026-11-03 — Xiaomi-OCR-0 and Russian (M4, 32 GB, MPS fp16)

Method: synthetic printed samples with ground truth; character error rate (CER) for
text, exact cell match for tables; four samples degraded (rotate + blur + JPEG q40 +
downscale) to imitate a phone photo.

| Sample | Backend | Result |
|--------|---------|--------|
| Russian paragraph, 270 chars | Xiaomi-OCR-0 | **CER 0.0000** (document and text prompts) |
| Same paragraph, degraded photo | Xiaomi-OCR-0 | **CER 0.0000** |
| Russian invoice snippet | Xiaomi-OCR-0 | **CER 0.0000** |
| Russian paragraph | Vision (`accurate`) | CER 0.0074 (`Nº` for `№`) |
| Russian paragraph | Vision (default before fix = `fast`) | CER 0.6889 — Latin transliteration |
| Russian paragraph | Paddle (`lang="ru"`) | CER 0.0037 |
| Russian table (4×5) | Xiaomi-OCR-0 | **40/40 cells**, correct `headers`/`rows` |
| English table (4×5) | Xiaomi-OCR-0 | **40/40 cells** |
| Russian table, degraded photo | Xiaomi-OCR-0 | **40/40 cells** |
| Full page (heading + prose + table) | Xiaomi-OCR-0 | table 40/40; prose CER 3.0% (one dropped letter) |
| Full page, degraded photo | Xiaomi-OCR-0 | table 38/40 (two dropped letters, all numbers correct) |

Language probe on clean renders (text prompt, CER):
`de 0.000`, `ja 0.000`, `el 0.019`, `ko 0.189`, `ar 0.400` — Arabic dropped every
digit, Korean confused glyphs. The model publishes no supported-language list, so
treat Russian/Latin/Japanese as "works in practice", not as a guarantee.

Timing: first request 131 s (Metal kernel warm-up), then 2.4–17.5 s per page on M4 MPS
fp16. Installing `flash-linear-attention` / `causal_conv1d` is reported by
`transformers` to speed this up further.

---

## Recommendations

### For production use today
- **Apple Vision** — fastest, zero install, best Cyrillic on macOS. Default for plain text.
- **Xiaomi-OCR-0** — the only backend that returns document structure: Markdown, HTML
  tables, LaTeX formulas, and KIE JSON. Use it for invoices, specifications, reports.

### PaddleOCR (CPU)
Use as a cross-platform fallback when:
- Not on macOS
- Vision's language support is insufficient
- You do not want to download the Xiaomi model

Note: Paddle table extraction needs PaddleOCR >= 3.0 (`PPStructureV3`).
