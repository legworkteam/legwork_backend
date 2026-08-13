from pathlib import Path

import cv2
import numpy as np


def generate_demo_image(text: str, output_path: Path) -> None:
    canvas = np.full((640, 1600, 3), 255, dtype=np.uint8)
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 3.0
    thickness = 7
    text_size, _ = cv2.getTextSize(text, font, scale, thickness)
    x = max(40, (canvas.shape[1] - text_size[0]) // 2)
    y = max(120, (canvas.shape[0] + text_size[1]) // 2)
    cv2.putText(canvas, text, (x, y), font, scale, (0, 0, 0), thickness, cv2.LINE_AA)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), canvas)


if __name__ == "__main__":
    output = Path("data") / "temporary" / "ocr-demo-DEMO-BAG-001.png"
    generate_demo_image("DEMO-BAG-001", output)
    print(output)
