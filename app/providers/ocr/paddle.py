from __future__ import annotations

import os
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import anyio
import cv2
import numpy as np

from app.core.exceptions import ProviderError
from app.providers.ocr.base import OcrDetection, OcrPreprocessVariant, OcrProvider, OcrResult

try:
    from paddleocr import PaddleOCR
except ImportError:  # pragma: no cover
    PaddleOCR = None


def preprocess_primary_image(image_path: str) -> np.ndarray:
    image = _load_image(image_path)
    resized = _resize_for_ocr(image)
    grayscale = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    denoised = cv2.bilateralFilter(grayscale, 9, 50, 50)
    contrasted = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(denoised)
    _, thresholded = cv2.threshold(contrasted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresholded


def preprocess_secondary_image(image_path: str) -> np.ndarray:
    image = _load_image(image_path)
    resized = _resize_for_ocr(image)
    grayscale = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(grayscale, (3, 3), 0)
    adaptive = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    sharpened = cv2.filter2D(adaptive, -1, kernel)
    return sharpened


def _load_image(image_path: str) -> np.ndarray:
    image = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if image is None:
        raise ProviderError("OCR 입력 이미지를 불러오지 못했습니다.")
    return image


def _resize_for_ocr(image: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    long_side = max(height, width)
    short_side = min(height, width)

    scale = 1.0
    if long_side > 2200:
        scale = 2200 / long_side
    elif short_side < 900:
        scale = 900 / short_side

    if scale == 1.0:
        return image

    new_width = max(1, int(width * scale))
    new_height = max(1, int(height * scale))
    return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)


class PaddleOcrProvider(OcrProvider):
    def __init__(self) -> None:
        if PaddleOCR is None:  # pragma: no cover
            raise ProviderError("PaddleOCR가 설치되어 있지 않습니다.")

        os.environ.setdefault("FLAGS_enable_pir_api", "0")
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        try:
            self._ocr = PaddleOCR(
                text_detection_model_name="PP-OCRv5_mobile_det",
                text_recognition_model_name="en_PP-OCRv5_mobile_rec",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                enable_mkldnn=False,
            )
        except Exception as exc:  # pragma: no cover
            raise ProviderError("OCR Provider 초기화에 실패했습니다.") from exc

    async def recognize(
        self,
        *,
        image_path: str,
        variant: OcrPreprocessVariant = OcrPreprocessVariant.PRIMARY,
    ) -> OcrResult:
        return await anyio.to_thread.run_sync(self._recognize_sync, image_path, variant)

    def _recognize_sync(self, image_path: str, variant: OcrPreprocessVariant) -> OcrResult:
        started_at = perf_counter()
        preprocessed_path = self._write_preprocessed_image(image_path, variant)
        try:
            raw_output = list(self._ocr.predict(preprocessed_path))
        except Exception as exc:
            raise ProviderError("OCR 인식에 실패했습니다.") from exc
        finally:
            Path(preprocessed_path).unlink(missing_ok=True)

        detections = _parse_paddle_output(raw_output)
        return OcrResult(
            detections=detections,
            raw_texts=[detection.text for detection in detections],
            processing_time_ms=int((perf_counter() - started_at) * 1000),
        )

    def _write_preprocessed_image(
        self,
        image_path: str,
        variant: OcrPreprocessVariant,
    ) -> str:
        if variant is OcrPreprocessVariant.PRIMARY:
            processed = preprocess_primary_image(image_path)
        else:
            processed = preprocess_secondary_image(image_path)

        path = Path(image_path)
        output_path = path.with_name(f"{path.stem}-{variant.value}-{uuid4().hex}.png")
        if not cv2.imwrite(str(output_path), processed):
            raise ProviderError("OCR 전처리 결과 저장에 실패했습니다.")
        return str(output_path)


def _parse_paddle_output(raw_output: object) -> list[OcrDetection]:
    detections: list[OcrDetection] = []
    if not isinstance(raw_output, list):
        return detections

    for page in raw_output:
        if isinstance(page, dict):
            rec_texts = page.get("rec_texts") or []
            rec_scores = page.get("rec_scores") or []
            rec_polys = page.get("rec_polys") or []
        elif hasattr(page, "res"):
            result = getattr(page, "res")
            if not isinstance(result, dict):
                continue
            rec_texts = result.get("rec_texts") or []
            rec_scores = result.get("rec_scores") or []
            rec_polys = result.get("rec_polys") or []
        elif isinstance(page, list):
            for item in page:
                if not isinstance(item, (list, tuple)) or len(item) < 2:
                    continue
                points_raw, text_part = item[0], item[1]
                if (
                    not isinstance(text_part, (list, tuple))
                    or len(text_part) < 2
                    or not isinstance(text_part[0], str)
                ):
                    continue
                bounding_box = _to_bounding_box(points_raw)
                detections.append(
                    OcrDetection(
                        text=text_part[0],
                        confidence=float(text_part[1]),
                        bounding_box=bounding_box,
                    )
                )
            continue
        else:
            continue

        for index, text in enumerate(rec_texts):
            if not isinstance(text, str):
                continue
            score = float(rec_scores[index]) if index < len(rec_scores) else 0.0
            bounding_box = _to_bounding_box(rec_polys[index]) if index < len(rec_polys) else None
            detections.append(OcrDetection(text=text, confidence=score, bounding_box=bounding_box))
    return detections


def _to_bounding_box(points_raw: object) -> list[tuple[int, int]] | None:
    if not isinstance(points_raw, (list, tuple, np.ndarray)):
        return None
    bounding_box: list[tuple[int, int]] = []
    for point in points_raw:
        if isinstance(point, np.ndarray):
            point = point.tolist()
        if isinstance(point, (list, tuple)) and len(point) >= 2:
            bounding_box.append((int(point[0]), int(point[1])))
    return bounding_box or None
