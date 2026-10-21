"""Photograph detection and cropping — milestone 4.

A direct port of the embedded Python block from scan.sh: threshold the scan,
find photo-shaped contours, perspective-crop each one, save as sequential
JPGs. Pure functions (numpy/cv2 in, images out) so it stays unit-testable.

The detection heuristics are the ones that worked for scan.sh:
  * work on a downscaled copy so a 1200 DPI scan stays fast
  * everything darker than DARK_THRESHOLD counts as content
  * a candidate has to be big enough, not too elongated, mostly filled and
    not touching the edge of the page
"""

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

MAX_PHOTOS = 4
DARK_THRESHOLD = 215
MAX_WORK_WIDTH = 2400

MIN_AREA_RATIO = 0.015
MIN_FILL_RATIO = 0.45
MAX_ASPECT_RATIO = 3.5
JPEG_QUALITY = 95


class DetectionError(RuntimeError):
    """Raised when a scan contains no usable photographs."""


@dataclass(frozen=True)
class PhotoBox:
    """One detected photograph: its four corners and the contour area."""

    corners: np.ndarray  # 4x2 float32, in the coordinates of the full image
    area: float


def find_photo_boxes(
    image: np.ndarray,
    max_photos: int = MAX_PHOTOS,
    dark_threshold: int = DARK_THRESHOLD,
) -> list[PhotoBox]:
    """Find the photographs on a scanned page.

    Returns the boxes ordered top to bottom, left to right. Raises
    DetectionError when the page holds no usable photograph.
    """
    height, width = image.shape[:2]
    scale = min(1.0, MAX_WORK_WIDTH / float(width))
    if scale < 1:
        work = cv2.resize(
            image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA
        )
    else:
        work = image.copy()

    gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
    mask = cv2.threshold(gray, dark_threshold, 255, cv2.THRESH_BINARY_INV)[1]
    mask = cv2.morphologyEx(
        mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
    )
    mask = cv2.morphologyEx(
        mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    )
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    page_area = work.shape[0] * work.shape[1]
    border = max(8, int(min(work.shape[:2]) * 0.01))
    candidates: list[tuple[float, tuple, np.ndarray]] = []

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < page_area * MIN_AREA_RATIO:
            continue
        rect = cv2.minAreaRect(contour)
        (_, _), (rect_width, rect_height), _ = rect
        if rect_width <= 1 or rect_height <= 1:
            continue
        if area / (rect_width * rect_height) < MIN_FILL_RATIO:
            continue
        if max(rect_width, rect_height) / min(rect_width, rect_height) > MAX_ASPECT_RATIO:
            continue
        box = np.array(cv2.boxPoints(rect), dtype=np.float32)
        x_min, x_max = float(box[:, 0].min()), float(box[:, 0].max())
        y_min, y_max = float(box[:, 1].min()), float(box[:, 1].max())
        if (
            x_min <= border
            or y_min <= border
            or x_max >= work.shape[1] - border
            or y_max >= work.shape[0] - border
        ):
            continue
        candidates.append((area, rect[0], box))

    if not candidates:
        raise DetectionError("No photographs were detected.")

    # Keep the biggest ones, then number them in reading order.
    candidates.sort(key=lambda candidate: candidate[0], reverse=True)
    candidates = candidates[:max_photos]
    candidates.sort(key=lambda candidate: (candidate[1][1], candidate[1][0]))

    boxes = []
    for area, _center, box in candidates:
        corners = box / scale if scale != 1 else box
        boxes.append(PhotoBox(corners=_order_points(corners), area=area))
    return boxes


def crop_photo(image: np.ndarray, corners: np.ndarray) -> np.ndarray:
    """Cut one photograph out of the scan, straightened to its edges."""
    top_left, top_right, bottom_right, bottom_left = corners
    width = max(
        1,
        int(
            round(
                max(
                    np.linalg.norm(bottom_right - bottom_left),
                    np.linalg.norm(top_right - top_left),
                )
            )
        ),
    )
    height = max(
        1,
        int(
            round(
                max(
                    np.linalg.norm(top_right - bottom_right),
                    np.linalg.norm(top_left - bottom_left),
                )
            )
        ),
    )
    target = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    crop = cv2.warpPerspective(
        image,
        cv2.getPerspectiveTransform(corners, target),
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    if crop is None or crop.size == 0:
        raise DetectionError("Failed to crop one of the detected photographs.")
    return crop


def process_image(
    image: np.ndarray,
    output_dir: Path,
    start_number: int = 1,
    max_photos: int = MAX_PHOTOS,
) -> list[Path]:
    """Detect the photographs on an image and write them as numbered JPGs."""
    boxes = find_photo_boxes(image, max_photos=max_photos)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for index, box in enumerate(boxes):
        crop = crop_photo(image, box.corners)
        output = output_dir / f"{start_number + index:06d}.jpg"
        if not cv2.imwrite(str(output), crop, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]):
            raise DetectionError(f"Failed to write {output}")
        written.append(output)
    return written


def process_scan(
    scan_path: Path,
    output_dir: Path,
    start_number: int = 1,
    max_photos: int = MAX_PHOTOS,
) -> list[Path]:
    """Detect and crop the photographs of a scanned TIFF."""
    image = cv2.imread(str(scan_path), cv2.IMREAD_COLOR)
    if image is None:
        raise DetectionError("OpenCV could not read the scan.")
    return process_image(image, output_dir, start_number, max_photos)


def _order_points(points: np.ndarray) -> np.ndarray:
    """Sort four points as top-left, top-right, bottom-right, bottom-left."""
    points = np.array(points, dtype=np.float32)
    sums = points.sum(axis=1)
    diffs = np.diff(points, axis=1).reshape(-1)
    return np.array(
        [
            points[np.argmin(sums)],
            points[np.argmin(diffs)],
            points[np.argmax(sums)],
            points[np.argmax(diffs)],
        ],
        dtype=np.float32,
    )
