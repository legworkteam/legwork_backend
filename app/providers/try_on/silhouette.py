"""Procedural mannequin-silhouette avatar renderer.

Real (non-AI) implementation for avatar-only try-on (no uploaded photo). No
GPU or paid image-generation API is available for this scope (see
`openai_edit.py`'s docstring), so instead of an AI-generated body, this draws
a body-proportioned mannequin silhouette from the user's height/weight and
composites the real product photo(s) (already fetched to disk -- see
`payload.garment_image_paths`, resolved by the service layer) next to it as
photo cards. This is a stylized vector mannequin, not a photorealistic
render: that ceiling needs real image generation, which is the same
GPU/API-budget-blocked resource as photo-based try-on. Photo-based try-on (a
real person photo) is a separate scope and still goes through
OpenAITryOnProvider/Mock.
"""

from __future__ import annotations

import cv2
import numpy as np

from app.core.exceptions import GenerationFailedError
from app.modules.products.schemas import ProductDetail
from app.providers.try_on.base import TryOnProviderRequest, TryOnProviderResult

_CANVAS_W = 720
_CANVAS_H = 960
_BG = (247, 246, 244)
_OUTLINE = (72, 62, 52)
_FILL = (222, 213, 198)
_SHADOW = (200, 194, 184)
_CARD_BORDER = (40, 90, 150)
_TEXT = (45, 45, 45)


def render_avatar_silhouette(payload: TryOnProviderRequest) -> TryOnProviderResult:
    if payload.simulate_failure:
        raise GenerationFailedError("Avatar silhouette generation failure.")

    canvas = np.full((_CANVAS_H, _CANVAS_W, 3), _BG, dtype=np.uint8)
    body = _draw_mannequin(canvas, height_cm=payload.avatar.height_cm, weight_kg=payload.avatar.weight_kg)
    _draw_item_photo_cards(canvas, payload, hip_point=body["hip_point"])
    _draw_caption(canvas, payload)

    ok, encoded = cv2.imencode(".png", canvas)
    if not ok:
        raise GenerationFailedError("Failed to encode avatar silhouette image.")

    return TryOnProviderResult(
        filename="avatar-silhouette.png",
        content_type="image/png",
        content=encoded.tobytes(),
        provider="silhouette",
        metadata={"mode": "silhouette"},
    )


def _body_scale(height_cm: float, weight_kg: float) -> tuple[float, float]:
    """px-per-cm and a body-width multiplier derived from BMI (1.0 at BMI 22)."""
    height_m = height_cm / 100
    bmi = weight_kg / (height_m * height_m)
    width_scale = max(0.75, min(1.5, bmi / 22))
    px_per_cm = (_CANVAS_H * 0.68) / height_cm
    return px_per_cm, width_scale


def _tapered_limb(
    canvas: np.ndarray, mask: np.ndarray, *, p0: tuple[int, int], p1: tuple[int, int], w0: int, w1: int
) -> None:
    """Draw a limb as a quadrilateral tapering from width w0 at p0 to w1 at p1."""
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    length = max(1.0, (dx * dx + dy * dy) ** 0.5)
    nx, ny = -dy / length, dx / length  # unit normal
    poly = np.array(
        [
            [x0 + nx * w0 / 2, y0 + ny * w0 / 2],
            [x1 + nx * w1 / 2, y1 + ny * w1 / 2],
            [x1 - nx * w1 / 2, y1 - ny * w1 / 2],
            [x0 - nx * w0 / 2, y0 - ny * w0 / 2],
        ],
        dtype=np.int32,
    )
    for target, color in ((mask, 255), (canvas, _FILL)):
        cv2.fillConvexPoly(target, poly, color, cv2.LINE_AA)
    cv2.circle(mask, p0, w0 // 2, 255, -1, cv2.LINE_AA)
    cv2.circle(canvas, p0, w0 // 2, _FILL, -1, cv2.LINE_AA)
    cv2.circle(mask, p1, w1 // 2, 255, -1, cv2.LINE_AA)
    cv2.circle(canvas, p1, w1 // 2, _FILL, -1, cv2.LINE_AA)


def _apply_volume_shading(canvas: np.ndarray, mask: np.ndarray) -> None:
    """Soft left-lit / right-shadowed gradient over the body mask, to read as
    a rounded 3D form rather than flat cut-out shapes."""
    gradient = np.linspace(1.22, 0.82, _CANVAS_W, dtype=np.float32)
    gradient_img = np.tile(gradient, (_CANVAS_H, 1))
    body = mask > 0
    shaded = canvas.astype(np.float32)
    for c in range(3):
        channel = shaded[:, :, c]
        channel[body] = np.clip(channel[body] * gradient_img[body], 0, 255)
    canvas[:] = shaded.astype(np.uint8)


def _draw_mannequin(canvas: np.ndarray, *, height_cm: float, weight_kg: float) -> dict[str, tuple[int, int]]:
    px, width_scale = _body_scale(height_cm, weight_kg)
    cx = _CANVAS_W // 2
    top = int(_CANVAS_H * 0.06)
    mask = np.zeros((_CANVAS_H, _CANVAS_W), dtype=np.uint8)

    head_r = max(20, int(height_cm * 0.062 * px))
    head_cy = top + head_r
    cv2.circle(mask, (cx, head_cy), head_r, 255, -1, cv2.LINE_AA)
    cv2.circle(canvas, (cx, head_cy), head_r, _FILL, -1, cv2.LINE_AA)

    neck_w = max(10, int(head_r * 0.5))
    shoulder_y = head_cy + head_r - 2
    shoulder_w = int(height_cm * 0.24 * px * width_scale)
    waist_w = int(height_cm * 0.17 * px * width_scale)
    hip_w = int(height_cm * 0.20 * px * width_scale)
    torso_h = int(height_cm * 0.29 * px)
    waist_y = shoulder_y + int(torso_h * 0.62)
    hip_y = shoulder_y + torso_h

    torso = np.array(
        [
            [cx - shoulder_w // 2, shoulder_y],
            [cx + shoulder_w // 2, shoulder_y],
            [cx + waist_w // 2, waist_y],
            [cx + hip_w // 2, hip_y],
            [cx - hip_w // 2, hip_y],
            [cx - waist_w // 2, waist_y],
        ],
        dtype=np.int32,
    )
    cv2.fillPoly(mask, [torso], 255, cv2.LINE_AA)
    cv2.fillPoly(canvas, [torso], _FILL, cv2.LINE_AA)
    cv2.circle(mask, (cx, shoulder_y), neck_w, 255, -1, cv2.LINE_AA)
    cv2.circle(canvas, (cx, shoulder_y), neck_w, _FILL, -1, cv2.LINE_AA)

    shoulder_joint = max(12, int(height_cm * 0.028 * px))
    elbow_joint = max(9, int(shoulder_joint * 0.75))
    wrist_joint = max(7, int(shoulder_joint * 0.55))
    upper_arm = int(height_cm * 0.18 * px)
    forearm = int(height_cm * 0.16 * px)
    arm_points: list[tuple[int, int]] = []
    for side in (-1, 1):
        sx = cx + side * (shoulder_w // 2 - shoulder_joint // 2)
        sy = shoulder_y
        ex, ey = sx + side * int(upper_arm * 0.18), sy + upper_arm
        wx, wy = ex + side * int(forearm * 0.1), ey + forearm
        _tapered_limb(canvas, mask, p0=(sx, sy), p1=(ex, ey), w0=shoulder_joint, w1=elbow_joint)
        _tapered_limb(canvas, mask, p0=(ex, ey), p1=(wx, wy), w0=elbow_joint, w1=wrist_joint)
        arm_points.append((wx, wy))

    hip_joint = max(16, int(height_cm * 0.045 * px * width_scale))
    knee_joint = max(12, int(hip_joint * 0.75))
    ankle_joint = max(8, int(hip_joint * 0.55))
    thigh = int(height_cm * 0.24 * px)
    shin = int(height_cm * 0.22 * px)
    leg_gap = hip_joint // 2 + 8
    foot_y = hip_y
    for side in (-1, 1):
        hx = cx + side * leg_gap
        kx, ky = hx + side * 4, hip_y + thigh
        ax, ay = kx, ky + shin
        _tapered_limb(canvas, mask, p0=(hx, hip_y), p1=(kx, ky), w0=hip_joint, w1=knee_joint)
        _tapered_limb(canvas, mask, p0=(kx, ky), p1=(ax, ay), w0=knee_joint, w1=ankle_joint)
        foot_y = ay

    _apply_volume_shading(canvas, mask)

    # crisp unified outline drawn last, on top of the shaded fill. findContours needs
    # a hard binary mask -- the anti-aliased draw calls above leave partial
    # (0-255) edge pixels, which trace as a jagged/staircase outline otherwise.
    binary_mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)[1]
    binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    smoothed = [cv2.approxPolyDP(c, 1.5, True) for c in contours]
    cv2.drawContours(canvas, smoothed, -1, _OUTLINE, 2, cv2.LINE_AA)

    # ground shadow + pedestal, mannequin-display style
    base_w = int(hip_w * 1.3)
    cv2.ellipse(canvas, (cx, foot_y + 14), (base_w, 14), 0, 0, 360, _SHADOW, -1, cv2.LINE_AA)
    cv2.ellipse(canvas, (cx, foot_y + 14), (base_w, 14), 0, 0, 360, _OUTLINE, 1, cv2.LINE_AA)

    return {"hip_point": (cx + hip_w // 2, hip_y - int(torso_h * 0.15)), "arm_points": arm_points}


def _read_image(path: str) -> np.ndarray | None:
    # cv2.imread opens paths with fopen() under the hood and silently fails
    # on non-ASCII (e.g. Korean) path components on Windows -- read the
    # bytes with Python's own (Unicode-safe) open() and decode in memory.
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError:
        return None
    return cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)


def _center_crop_square(image: np.ndarray, size: int) -> np.ndarray:
    h, w = image.shape[:2]
    side = min(h, w)
    y0, x0 = (h - side) // 2, (w - side) // 2
    return cv2.resize(image[y0 : y0 + side, x0 : x0 + side], (size, size), interpolation=cv2.INTER_AREA)


def _labeled_garment_items(payload: TryOnProviderRequest) -> list[ProductDetail]:
    """Mirror the (product, then coordi items) collection order the service
    used to build `garment_image_paths`, so labels line up with images."""
    items: list[ProductDetail] = []
    if payload.product is not None and payload.product.thumbnail_file_id is not None:
        items.append(payload.product)
    for item in payload.coordi_items[:5]:
        if item.product.thumbnail_file_id is not None:
            items.append(item.product)
    return items


def _draw_item_photo_cards(
    canvas: np.ndarray, payload: TryOnProviderRequest, *, hip_point: tuple[int, int]
) -> None:
    pairs = list(zip(_labeled_garment_items(payload), payload.garment_image_paths))[:3]
    if not pairs:
        return

    hx, hy = hip_point
    card_size = 150
    card_x = min(hx + 50, _CANVAS_W - card_size - 24)
    card_y = max(20, hy - 40)
    for product, path in pairs:
        photo = _read_image(path)
        if photo is None:
            continue
        inset = 10
        thumb = _center_crop_square(photo, card_size - inset * 2)

        y2 = min(card_y + card_size, _CANVAS_H - 4)
        x2 = min(card_x + card_size, _CANVAS_W - 4)
        cv2.rectangle(canvas, (card_x, card_y), (x2, y2), (255, 255, 255), -1, cv2.LINE_AA)
        canvas[card_y + inset : card_y + inset + thumb.shape[0], card_x + inset : card_x + inset + thumb.shape[1]] = thumb
        cv2.rectangle(canvas, (card_x, card_y), (x2, y2), _CARD_BORDER, 2, cv2.LINE_AA)
        cv2.line(canvas, (hx, hy), (card_x, card_y + card_size // 2), _CARD_BORDER, 1, cv2.LINE_AA)
        cv2.putText(
            canvas, product.product_code, (card_x, y2 + 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, _TEXT, 1, cv2.LINE_AA,
        )
        card_y += card_size + 40


def _draw_caption(canvas: np.ndarray, payload: TryOnProviderRequest) -> None:
    line = f"{payload.avatar.gender.value} / {payload.avatar.height_cm:.0f}cm / {payload.avatar.weight_kg:.0f}kg"
    cv2.putText(canvas, line, (40, int(_CANVAS_H * 0.95)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, _TEXT, 1, cv2.LINE_AA)
