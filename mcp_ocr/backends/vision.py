"""Apple Vision OCR backend (macOS 10.15+)."""

import os
from mcp_ocr.backends.base import BaseOCRBackend, ErrorCode
from mcp_ocr.backends.lang import resolve_lang_code

_VISION_LANG_MAP = {
    "ru": ["ru-RU", "en-US"],
    "en": ["en-US"],
    "ch": ["zh-Hans", "zh-Hant", "en-US"],
    "zh": ["zh-Hans", "zh-Hant", "en-US"],
    "ja": ["ja-JP", "en-US"],
    "ko": ["ko-KR", "en-US"],
    "fr": ["fr-FR", "en-US"],
    "de": ["de-DE", "en-US"],
    "es": ["es-ES", "en-US"],
    "ar": ["ar-SA", "en-US"],
    "it": ["it-IT", "en-US"],
    "pt": ["pt-BR", "en-US"],
}


def _resolve_vision_langs(lang: str | None) -> list[str]:
    code = resolve_lang_code(lang, "en")
    return _VISION_LANG_MAP.get(code, ["en-US"])


class VisionBackend(BaseOCRBackend):
    name = "vision"
    tasks = ["text", "layout", "table"]

    def _load_image(self, path: str):
        import Vision
        import Quartz

        if not os.path.isfile(path):
            return None, {"success": False, "error": ErrorCode.ENOENT,
                          "detail": f"Cannot load image: {path}"}

        url = Quartz.CFURLCreateFromFileSystemRepresentation(
            None, path.encode("utf-8"), len(path.encode("utf-8")), False
        )
        src = Quartz.CGImageSourceCreateWithURL(url, None)
        if src is None:
            return None, {"success": False, "error": ErrorCode.ENOENT,
                          "detail": f"Cannot load image: {path}"}
        img = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)
        if img is None:
            return None, {"success": False, "error": ErrorCode.ENOENT,
                          "detail": f"Cannot decode image: {path}"}
        return img, None

    def _perform_ocr(self, img, lang: str | None = None, mode: str = "accurate") -> list[dict]:
        import Vision

        handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(img, None)
        request = Vision.VNRecognizeTextRequest.alloc().init()

        fast = mode == "fast"
        if fast:
            rev = (Vision.VNRecognizeTextRequestRevision2
                   if hasattr(Vision, "VNRecognizeTextRequestRevision2")
                   else Vision.VNRecognizeTextRequestRevision1)
        else:
            rev = (Vision.VNRecognizeTextRequestRevision3
                   if hasattr(Vision, "VNRecognizeTextRequestRevision3")
                   else Vision.VNRecognizeTextRequestRevision2
                   if hasattr(Vision, "VNRecognizeTextRequestRevision2")
                   else Vision.VNRecognizeTextRequestRevision1)
        request.setRevision_(rev)
        # Only the accurate recognizer supports non-Latin scripts; the fast
        # recognizer reports just a handful of Latin languages, so treating any
        # unknown mode as "fast" silently breaks Cyrillic, CJK and Greek.
        request.setRecognitionLevel_(
            Vision.VNRequestTextRecognitionLevelFast if fast
            else Vision.VNRequestTextRecognitionLevelAccurate
        )
        request.setUsesLanguageCorrection_(True)
        request.setRecognitionLanguages_(_resolve_vision_langs(lang))

        success, error = handler.performRequests_error_([request], None)
        if not success:
            err_msg = error.localizedDescription() if error else "Vision request failed"
            raise RuntimeError(err_msg)

        observations = request.results() or []
        lines = []
        for obs in observations:
            text = obs.topCandidates_(1)[0].string()
            confidence = float(obs.topCandidates_(1)[0].confidence())
            bb = obs.boundingBox()
            lines.append({
                "text": text,
                "confidence": round(confidence, 4),
                "bbox": [
                    round(float(bb.origin.x), 4),
                    round(float(bb.origin.y), 4),
                    round(float(bb.size.width), 4),
                    round(float(bb.size.height), 4),
                ],
            })
        return lines

    def extract(self, path: str, lang: str | None = None, mode: str = "accurate") -> dict:
        img, err = self._load_image(path)
        if err:
            return err
        try:
            lines = self._perform_ocr(img, lang, mode)
            full_text = "\n".join(line["text"] for line in lines)
            return {"success": True, "text": full_text, "lines": lines}
        except Exception as e:
            return {"success": False, "error": ErrorCode.EPROCESSING, "detail": str(e)}

    def layout(self, path: str, lang: str | None = None, mode: str = "accurate") -> dict:
        result = self.extract(path, lang, mode)
        if not result.get("success"):
            return result
        blocks = []
        for line in result.get("lines", []):
            bb = line["bbox"]
            blocks.append({
                "type": "text",
                "text": line["text"],
                "confidence": line["confidence"],
                "x": bb[0],
                "y": bb[1],
                "width": bb[2],
                "height": bb[3],
            })
        return {"success": True, "blocks": blocks}

    def table(self, path: str, lang: str | None = None, mode: str = "accurate") -> dict:
        """Vision OCR returns text lines only — it cannot recover table structure.

        Apple exposes table parsing through ``VNRecognizeDocumentsRequest``, which
        the pinned pyobjc framework does not provide, so this backend has no honest
        table implementation. Report that instead of returning text as a "table".
        """
        if not os.path.isfile(path):
            return {"success": False, "error": ErrorCode.ENOENT,
                    "detail": f"File not found: {path}"}
        return {
            "success": False,
            "error": ErrorCode.EUNSUPPORTED,
            "detail": (
                "Apple Vision has no table-structure output in this build: pyobjc "
                "does not expose VNRecognizeDocumentsRequest. Use ocr_table_xiaomi "
                "(recommended) or ocr_table_paddle. Upgrade pyobjc-framework-Vision "
                "to enable it in the future."
            ),
        }
