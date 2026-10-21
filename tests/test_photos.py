"""Tests for the photo detection and cropping pipeline — milestone 4.

The tests build synthetic pages (a white sheet with dark rectangles standing
in for photographs) so they run without a scanner attached.
"""

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from scan_gui.processing import photos
from scan_gui.processing.photos import DetectionError

# Two photographs on a 1000x800 page.
LEFT_PHOTO = (100, 100, 400, 500)
RIGHT_PHOTO = (500, 100, 800, 500)


def make_page(rectangles=(LEFT_PHOTO, RIGHT_PHOTO), size=(1000, 800)):
    """A white page with dark rectangles on it."""
    page = np.full((size[1], size[0], 3), 255, dtype=np.uint8)
    for x1, y1, x2, y2 in rectangles:
        page[y1:y2, x1:x2] = 60
    return page


class FindPhotoBoxesTest(unittest.TestCase):
    def test_finds_every_photograph(self):
        boxes = photos.find_photo_boxes(make_page())
        self.assertEqual(len(boxes), 2)

    def test_box_corners_match_the_photograph(self):
        boxes = photos.find_photo_boxes(make_page())
        for box, (x1, y1, x2, y2) in zip(boxes, (LEFT_PHOTO, RIGHT_PHOTO)):
            corners = box.corners
            self.assertAlmostEqual(float(corners[:, 0].min()), x1, delta=2)
            self.assertAlmostEqual(float(corners[:, 0].max()), x2, delta=2)
            self.assertAlmostEqual(float(corners[:, 1].min()), y1, delta=2)
            self.assertAlmostEqual(float(corners[:, 1].max()), y2, delta=2)

    def test_photographs_are_ordered_in_reading_order(self):
        page = make_page(
            ((100, 100, 400, 500), (500, 100, 800, 500), (100, 550, 400, 780))
        )
        boxes = photos.find_photo_boxes(page)
        self.assertEqual(len(boxes), 3)
        centres = [(float(b.corners[:, 1].mean()), float(b.corners[:, 0].mean()))
                   for b in boxes]
        self.assertEqual(centres, sorted(centres))

    def test_area_is_reported(self):
        boxes = photos.find_photo_boxes(make_page())
        expected = (LEFT_PHOTO[2] - LEFT_PHOTO[0]) * (LEFT_PHOTO[3] - LEFT_PHOTO[1])
        self.assertAlmostEqual(boxes[0].area, expected, delta=expected * 0.05)

    def test_blank_page_raises(self):
        blank = np.full((800, 1000, 3), 255, dtype=np.uint8)
        with self.assertRaises(DetectionError):
            photos.find_photo_boxes(blank)

    def test_photograph_touching_the_edge_is_ignored(self):
        page = make_page(((0, 100, 300, 500),))
        with self.assertRaises(DetectionError):
            photos.find_photo_boxes(page)

    def test_small_marks_are_ignored(self):
        page = make_page(((600, 600, 640, 640),))
        with self.assertRaises(DetectionError):
            photos.find_photo_boxes(page)

    def test_max_photos_is_respected(self):
        rectangles = tuple(
            (100 + 350 * index, 100, 250 + 350 * index, 400) for index in range(6)
        )
        boxes = photos.find_photo_boxes(make_page(rectangles, size=(2400, 800)))
        self.assertEqual(len(boxes), photos.MAX_PHOTOS)


class CropPhotoTest(unittest.TestCase):
    def test_crop_has_the_size_of_the_photograph(self):
        page = make_page()
        box = photos.find_photo_boxes(page)[0]
        crop = photos.crop_photo(page, box.corners)
        self.assertAlmostEqual(crop.shape[1], 300, delta=2)  # width
        self.assertAlmostEqual(crop.shape[0], 400, delta=2)  # height

    def test_crop_contains_the_photograph_content(self):
        page = make_page()
        box = photos.find_photo_boxes(page)[0]
        crop = photos.crop_photo(page, box.corners)
        self.assertLess(float(crop.mean()), 120)  # dark photo, not white page


class ProcessImageTest(unittest.TestCase):
    def test_writes_numbered_files(self):
        page = make_page()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            written = photos.process_image(page, output)
            self.assertEqual(
                [path.name for path in written], ["000001.jpg", "000002.jpg"]
            )
            for path in written:
                self.assertTrue(path.exists())
                self.assertGreater(path.stat().st_size, 0)
                self.assertTrue(cv2.imread(str(path)) is not None)

    def test_numbering_continues(self):
        page = make_page()
        with tempfile.TemporaryDirectory() as tmp:
            written = photos.process_image(page, Path(tmp), start_number=7)
            self.assertEqual(
                [path.name for path in written], ["000007.jpg", "000008.jpg"]
            )

    def test_creates_the_output_directory(self):
        page = make_page()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "photos"
            written = photos.process_image(page, output)
            self.assertTrue(output.is_dir())
            self.assertEqual(len(written), 2)


class ProcessScanTest(unittest.TestCase):
    def test_reads_a_tiff_and_writes_photos(self):
        with tempfile.TemporaryDirectory() as tmp:
            scan = Path(tmp) / "000001.tiff"
            self.assertTrue(cv2.imwrite(str(scan), make_page()))
            output = Path(tmp) / "photos"
            written = photos.process_scan(scan, output)
            self.assertEqual(len(written), 2)
            self.assertTrue(all(path.exists() for path in written))

    def test_unreadable_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp) / "000001.tiff"
            broken.write_text("not an image")
            with self.assertRaises(DetectionError):
                photos.process_scan(broken, Path(tmp))


if __name__ == "__main__":
    unittest.main()
