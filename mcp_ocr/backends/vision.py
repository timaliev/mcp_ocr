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

    def __init__(self):
        self._has_table_support = False
        try:
            import Vision
            if hasattr(Vision, "VNRecognizeTextRequestRevision4"):
                self._has_table_support = True
        except ImportError:
            pass

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

        if mode == "fast":
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
        request.setRecognitionLevel_(
            Vision.VNRequestTextRecognitionLevelAccurate if mode == "accurate"
            else Vision.VNRequestTextRecognitionLevelFast
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
        if not self._has_table_support:
            return {"success": False, "error": ErrorCode.EUNSUPPORTED,
                    "detail": "Table detection requires macOS 15+ (use ocr_text_vision instead)"}

        import Vision, Quartz

        img, err = self._load_image(path)
        if err:
            return err

        try:
            handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(img, None)
            request = Vision.VNRecognizeTextRequest.alloc().init()
            request.setRevision_(Vision.VNRecognizeTextRequestRevision4)
            request.setRecognitionLevel_(
                Vision.VNRequestTextRecognitionLevelAccurate if mode == "accurate"
                else Vision.VNRequestTextRecognitionLevelFast
            )
            request.setUsesLanguageCorrection_(True)
            request.setAutomaticallyDetectsTextLanguage_(True)
            handler.performRequests_error_([request], None)

            tables = []
            for obs in request.results() or []:
                text = obs.topCandidates_(1)[0].string()
                tables.append({"text": text, "csv": "", "headers": [], "rows": []})
            return {"success": True, "tables": tables}
        except Exception as e:
            return {"success": False, "error": ErrorCode.EPROCESSING, "detail": str(e)}
