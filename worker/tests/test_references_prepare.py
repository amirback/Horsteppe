"""Подготовка снимка пользователя: поворот, размер, отказ от лишнего сжатия.

Здесь проверяется то, что обычно узнают от пользователя: товар приехал боком,
потому что телефон записал поворот в метаданные, а не в пиксели.

EXIF собирается байтами вручную — записать его нечем, Pillow в зависимостях
нет. Зато разбор проверяется ровно на тех данных, которые приходят от камеры.

Ни сети, ни ключей, ни денег.
"""
from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path

WORKER_DIR = Path(__file__).resolve().parent.parent
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

import media  # noqa: E402
import references  # noqa: E402
from references import ReferenceError  # noqa: E402


def jpeg_with_orientation(orientation: int, body: bytes = b"\xff\xdb\x00\x04\x00\x00") -> bytes:
    """Минимальный JPEG с одним тегом Orientation в APP1."""
    tiff = bytearray(b"II" + struct.pack("<HI", 42, 8))
    tiff += struct.pack("<H", 1)                       # одна запись в IFD0
    tiff += struct.pack("<HHI", 0x0112, 3, 1)          # тег, тип SHORT, одно значение
    tiff += struct.pack("<HH", orientation, 0)         # значение + добивка
    tiff += struct.pack("<I", 0)                       # следующего IFD нет
    payload = b"Exif\x00\x00" + bytes(tiff)
    app1 = b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload
    return b"\xff\xd8" + app1 + body + b"\xff\xd9"


def make_image(path: Path, width: int, height: int) -> None:
    media.run_ffmpeg([
        "-f", "lavfi", "-i", f"testsrc2=size={width}x{height}",
        "-frames:v", "1", str(path),
    ])


class TestExif(unittest.TestCase):
    def test_reads_every_orientation_a_camera_writes(self) -> None:
        for value in range(1, 9):
            with self.subTest(orientation=value):
                self.assertEqual(references.read_exif_orientation(jpeg_with_orientation(value)), value)

    def test_no_exif_means_as_shot(self) -> None:
        self.assertEqual(references.read_exif_orientation(b"\xff\xd8\xff\xd9"), 1)

    def test_png_has_no_orientation_and_that_is_fine(self) -> None:
        self.assertEqual(references.read_exif_orientation(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32), 1)

    def test_garbage_does_not_crash_the_upload(self) -> None:
        self.assertEqual(references.read_exif_orientation(b"\xff\xd8" + b"\xff\xe1\x00\x08abcd"), 1)
        self.assertEqual(references.read_exif_orientation(b""), 1)

    def test_rotated_photo_is_actually_turned(self) -> None:
        """Ориентация 6 — обычный вертикальный снимок телефона."""
        self.assertEqual(references._ORIENTATION_FILTER[6], "transpose=1")
        self.assertEqual(references._ORIENTATION_FILTER[1], "")


class TestNormalize(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_good_photo_is_passed_through_untouched(self) -> None:
        """Лучший исход — не тронуть файл: пересжатие стоило бы резкости."""
        src = self.root / "src.png"
        make_image(src, 1000, 1200)
        result = references.normalize(src, self.root, "ref_0", "image/png")
        self.assertFalse(result["recompressed"])
        self.assertFalse(result["downscaled"])
        self.assertEqual(result["path"].read_bytes(), src.read_bytes())

    def test_oversized_photo_is_fitted_without_stretching(self) -> None:
        src = self.root / "big.png"
        make_image(src, 4000, 3000)
        result = references.normalize(src, self.root, "ref_0", "image/png")
        self.assertTrue(result["downscaled"])
        self.assertLessEqual(max(result["width"], result["height"]), references.MAX_SIDE)
        self.assertAlmostEqual(result["width"] / result["height"], 4000 / 3000, places=2)

    def test_unusable_photo_is_refused_with_a_reason(self) -> None:
        src = self.root / "tiny.png"
        make_image(src, 64, 64)
        with self.assertRaises(ReferenceError) as raised:
            references.normalize(src, self.root, "ref_0", "image/png")
        self.assertIn("64", str(raised.exception))

    def test_foreign_format_is_refused_before_reading(self) -> None:
        with self.assertRaises(ReferenceError):
            references.normalize(self.root / "nothing.gif", self.root, "ref_0", "image/gif")

    def test_empty_file_is_refused(self) -> None:
        src = self.root / "empty.png"
        src.write_bytes(b"")
        with self.assertRaises(ReferenceError):
            references.normalize(src, self.root, "ref_0", "image/png")

    def test_weak_photo_is_flagged_not_blocked(self) -> None:
        """ТЗ §21: предупредить, но не отказывать — человек вправе попробовать."""
        src = self.root / "small.png"
        make_image(src, 400, 500)
        result = references.normalize(src, self.root, "ref_0", "image/png")
        self.assertIsNotNone(result["note"])
        self.assertIn("400", result["note"])

    def test_strong_photo_gets_no_complaint(self) -> None:
        self.assertIsNone(references.quality_note(1080, 1350))


if __name__ == "__main__":
    unittest.main()
