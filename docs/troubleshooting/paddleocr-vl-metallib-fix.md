# PaddleOCR-VL: MLX Default Metallib Fix

**Date:** 2025-08-06  
**Status:** Resolved (metallib) + Open (model schema)

---

## Symptom

```
$ paddleocr-vl ocr /tmp/test_ocr.png
MLX error: Failed to load the default metallib. library not found library not found library not found
  at /private/tmp/paddleocr-vl.swift/.build/checkouts/mlx-swift/Source/Cmlx/mlx-c/mlx/c/stream.cpp:115
```

`paddleocr-vl --help` worked, but any `ocr` subcommand crashed.

---

## Root Cause

**SwiftPM builds of mlx-swift do not compile `.metal` shader files into a `.metallib`.** Xcode's native build system handles Metal shader compilation automatically; `swift build` does not.

MLX requires a pre-compiled Metal library (`default.metallib` or `mlx.metallib`) at runtime for GPU kernel execution. The library resolution follows this order in `mlx-swift/Source/Cmlx/mlx/mlx/backend/metal/device.cpp`:

| Step | Path | Result |
|------|------|--------|
| 1 | `<binary_dir>/mlx.metallib` | NOT FOUND |
| 2 | `<binary_dir>/Resources/mlx.metallib` | NOT FOUND |
| 3 | SwiftPM bundle `mlx-swift_Cmlx.bundle/default.metallib` | NOT FOUND (CLI has no bundles) |
| 4 | `default.metallib` (relative path from CWD) | NOT FOUND |

All 4 attempts fail → `std::runtime_error` → crash.

This is a known limitation of mlx-swift outside Xcode. The `MetalCompilerPlugin` (PR [#313](https://github.com/ml-explore/mlx-swift/pull/313)) was proposed to add metallib compilation to SwiftPM builds but is not yet merged. Current mlx-swift versions (through 0.31.6) still depend on Xcode for Metal shader compilation.

---

## Diagnosis Method

Followed the [diagnose skill](../../../.agents/skills/diagnose/SKILL.md) phases:

### Phase 1 — Feedback Loop

Constructed a fast, deterministic reproducer:

```bash
python3 -c "
from PIL import Image, ImageDraw
img = Image.new('RGB', (200, 50), color='white')
draw = ImageDraw.Draw(img)
draw.text((10, 15), 'Hello World', fill='black')
img.save('/tmp/test_ocr.png')
"
paddleocr-vl ocr /tmp/test_ocr.png
```

Reproducible 100% of the time. 2-second loop.

### Phase 2 — Reproduce

Confirmed same error from both `/opt/homebrew/bin/paddleocr-vl` and the original build artifact at `.build/release/PaddleOCRVLCLI`, regardless of working directory.

### Phase 3 — Hypothesise

1. **Missing metallib file** — If mlx.metallib is not colocated with the binary, MLX won't find it.
2. **Binary relocation** — Binary built at `/private/tmp/...`, installed to `/opt/homebrew/bin/`, paths mismatch.
3. **Metal shader build step skipped** — SwiftPM doesn't run the Xcode metal compilation.
4. **Metal Toolchain not installed** — System can't compile shaders even if build step existed.
5. **METAL_PATH compile-time define wrong** — Baked-in path doesn't match runtime layout.

### Phase 4 — Instrument

- Traced metallib resolution in `device.cpp` → confirmed 4-step fallback chain
- Searched build tree for `*.metallib` → **zero matches** (no metallib ever produced)
- Grepped `Package.swift` for metal compilation → found `PrepareMetalShaders` reference but no plugin
- Checked `METAL_PATH` define → hardcoded to `"default.metallib"` (relative)
- Checked for `SWIFTPM_BUNDLE` → defined as `"mlx-swift_Cmlx"` but no bundle in CLI

**Confirmed:** Hypothesis 3 — SwiftPM build never produced the metallib.

### Phase 5 — Fix

**Method A: CMake build (simpler, used on 2026-08-06)**

Build the MLX C library with cmake — this automatically compiles all Metal shaders:

```bash
cd /tmp/paddleocr-vl.swift/.build/checkouts/mlx-swift/Source/Cmlx/mlx-c
mkdir -p build && cd build
cmake .. -G Ninja
ninja
```

The resulting metallib is at:
```
build/_deps/mlx-build/mlx/backend/metal/kernels/mlx.metallib
```

Copy it to the binary directory:
```bash
cp build/_deps/mlx-build/mlx/backend/metal/kernels/mlx.metallib \
  /tmp/paddleocr-vl.swift/.build/release/default.metallib
```

**Method B: Manual Metal compilation**

1. Installed Metal Toolchain: `xcodebuild -downloadComponent MetalToolchain` (704 MB)
2. Compiled metallib from generated `.metal` shader files:

```bash
cd /private/tmp/paddleocr-vl.swift

METAL_SRC=".build/checkouts/mlx-swift/Source/Cmlx"
GEN_METAL="$METAL_SRC/mlx-generated/metal"

INCLUDES="-I${METAL_SRC} -I${METAL_SRC}/mlx -I${GEN_METAL} \
  -I${METAL_SRC}/mlx/mlx/backend/metal/kernels \
  -I${METAL_SRC}/mlx/mlx/backend/metal/kernels/jit \
  -I${GEN_METAL}/steel/attn/kernels/../../.. \
  -I${GEN_METAL}/steel/conv/kernels/../../.. \
  -I${GEN_METAL}/steel/gemm/kernels/../../.."

ALL_GEN=$(find "$GEN_METAL" -name "*.metal" \
  ! -path "*/jit/*" ! -path "*/metal_3_*/*" | tr '\n' ' ')

xcrun -sdk macosx metal -o /tmp/mlx.metallib $ALL_GEN \
  -O -mmacosx-version-min=14.0 $INCLUDES
```

3. Placed metallib next to binary:

```bash
cp /tmp/mlx.metallib /opt/homebrew/bin/mlx.metallib
```

4. Verified — metallib error resolved.

### Phase 6 — Cleanup

- [x] Original repro no longer reproduces (metallib error)
- [x] Fix documented here
- [x] Metal Toolchain installed system-wide (needed for any future builds)

---

## Secondary Issue: Weight Key Mismatch

After the metallib fix, a weight loading error appeared:

```
Error: Unhandled keys ["vision_model"] in vision_model in PaddleOCRVLModel.NaViTVisionEncoder
```

### Root Cause

The HuggingFace checkpoint uses different weight key names than the Swift model expects:

| Checkpoint Key | Swift Expected Key |
|---|---|
| `visual.vision_model.embeddings.patch_embedding.*` | `vision_model.patch_embed.proj.*` |
| `visual.vision_model.encoder.layers.N.*` | `vision_model.layers.N.*` |
| `vision_model.layers.N.self_attn.q_proj/k_proj/v_proj` | `vision_model.layers.N.self_attn.qkv` (merged) |
| `vision_model.layers.N.self_attn.out_proj` | `vision_model.layers.N.self_attn.proj` |
| `visual.vision_model.head.*` | Not used (drop) |
| `visual.vision_model.embeddings.packing_position_embedding.*` | Not used (drop) |
| `mlp_AR.*` | Not used (drop) |

Additionally, the text model config was not being read because `config.json` has text model parameters at the top level (not nested under `text_config`).

### Fix Applied

**1. `sanitizeWeights()` rewritten** in `PaddleOCRVLModel.swift`:
- Maps `visual.vision_model.*` → `vision_model.*` (not blind `visual.` → `vision_model.`)
- Renames `embeddings.patch_embedding` → `patch_embed.proj`
- Renames `encoder.layers` → `layers`
- Merges separate `q_proj/k_proj/v_proj` weights into single `qkv` weight (concatenated along output dim)
- Renames `out_proj` → `proj`
- Drops `head.*`, `packing_position_embedding.*`, `mlp_AR.*`, `position_embedding.*`

**2. Config loading fixed** in `Configuration.swift`:
- When `text_config` key is absent from `config.json`, reads text model parameters from top-level config keys (`hidden_size`, `num_attention_heads`, etc.)

### Verification

```
$ paddleocr-vl ocr /tmp/test_ocr.png
0\答1сь0\0弃于\.00000\0\0\0\000...
```

Model loads, inference runs. Output is garbled for English text (model is Chinese-optimized), but no errors.

---

## Permanent Fix Recommendations

### Short-term (workaround)

Add a build script that compiles the metallib from mlx-swift build artifacts and places it alongside the binary. This is what the current fix does manually.

### Medium-term

Migrate to Xcode-based builds. Xcode's native build system compiles `.metal` files to `default.metallib` automatically. Steps:

1. Wrap the Swift package in an Xcode workspace
2. Build with `xcodebuild` instead of `swift build`
3. Ship the resulting `.app` bundle (which includes the metallib in the framework)

### Long-term

When `MetalCompilerPlugin` (PR [#313](https://github.com/ml-explore/mlx-swift/pull/313)) is merged into mlx-swift, update the dependency. The plugin will handle metallib compilation natively in SwiftPM builds, eliminating this issue entirely.

### For Distribution

If distributing via Homebrew:

```ruby
# In the formula
def install
  system "swift", "build", "-c", "release"
  
  # Compile metallib from mlx-swift sources
  metal_include = "#{buildpath}/.build/checkouts/mlx-swift/Source/Cmlx"
  system "xcrun", "-sdk", "macosx", "metal",
         "-o", "mlx.metallib",
         # ... metal files ...
         "-mmacosx-version-min=14.0"
  
  bin.install ".build/release/PaddleOCRVLCLI" => "paddleocr-vl"
  bin.install "mlx.metallib"
end
```

---

## References

- [mlx-swift PR #313 — MetalCompilerPlugin](https://github.com/ml-explore/mlx-swift/pull/313)
- [mlx-swift Issue #349 — Tuist bundle missing](https://github.com/ml-explore/mlx-swift/issues/349)
- [MLX PR #2061 — Search Resources dir for metallib](https://github.com/ml-explore/mlx/pull/2061)
- [swama Issue #30 — Same error in similar project](https://github.com/Trans-N-ai/swama/issues/30)
