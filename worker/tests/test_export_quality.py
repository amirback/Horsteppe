"""Качество экспорта: пересжатия и старт воспроизведения в браузере.

Что здесь доказывается на настоящих файлах, а не на виде кода:

1. `+faststart` действительно переносит индекс в начало файла — без него
   браузер ждёт полной загрузки, прежде чем показать первый кадр (ТЗ §26);
2. разделение профилей сжатия действительно уменьшает потери: сегмент внутри
   сборки пересжимается два-три раза, и раньше каждый проход шёл с тем же
   CRF 20, что и финал. Ошибки складывались.

Ни сети, ни ключей, ни денег: всё строится из сгенерированной FFmpeg картинки.

Запуск (из каталога worker):
    PYTHONUTF8=1 python -m pytest tests/test_export_quality.py -q
"""
from __future__ import annotations

import inspect
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WORKER_DIR = Path(__file__).resolve().parent.parent
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

import media  # noqa: E402

SIZE = (270, 480)  # маленький кадр: тест про профили сжатия, а не про разрешение


def moov_before_mdat(path: Path) -> bool:
    """Индекс mp4 лежит раньше самих данных — это и есть faststart."""
    raw = path.read_bytes()
    moov, mdat = raw.find(b"moov"), raw.find(b"mdat")
    assert moov != -1 and mdat != -1, "в файле нет атомов moov/mdat"
    return moov < mdat


def detailed_source(path: Path, seconds: float = 1.0) -> None:
    """Картинка с мелкой фактурой: на ровной заливке потери сжатия не видны."""
    w, h = SIZE
    media.run_ffmpeg([
        "-f", "lavfi", "-i", f"mandelbrot=size={w}x{h}:rate={media.FPS}",
        "-t", f"{seconds}", "-c:v", "libx264", "-preset", "veryfast", "-qp", "0",
        "-pix_fmt", "yuv420p", str(path),
    ])


def psnr_against(processed: Path, reference: Path) -> float:
    """Среднее PSNR в дБ: насколько далеко ушёл файл от исходника."""
    proc = subprocess.run(
        [media.ffmpeg_path(), "-hide_banner", "-i", str(processed), "-i", str(reference),
         "-lavfi", "psnr", "-f", "null", "-"],
        capture_output=True, text=True, timeout=300,
    )
    match = re.search(r"average:([0-9.]+)", proc.stderr)
    assert match, f"ffmpeg не вернул PSNR:\n{proc.stderr[-800:]}"
    return float(match.group(1))


def reencode(source: Path, out: Path, profile: list[str]) -> None:
    media.run_ffmpeg(["-i", str(source), *profile, "-an", str(out)])


class TestProfiles(unittest.TestCase):
    def test_final_profile_starts_playing_before_full_download(self) -> None:
        self.assertIn("+faststart", media._ENCODE_FINAL)

    def test_intermediate_keeps_more_detail_than_final(self) -> None:
        """Внутри сборки качество важнее веса: файл всё равно будет пересжат."""
        crf = lambda p: int(p[p.index("-crf") + 1])  # noqa: E731
        self.assertLess(crf(media._ENCODE_INTERMEDIATE), crf(media._ENCODE_FINAL))

    def test_subtitle_burn_is_the_last_pass_by_default(self) -> None:
        default = inspect.signature(media.burn_subtitles).parameters["final"].default
        self.assertTrue(default, "вшивание субтитров — последний видеопроход сборки")

    def test_intermediate_steps_do_not_pay_for_faststart(self) -> None:
        self.assertNotIn("-movflags", media._ENCODE_INTERMEDIATE)


class TestRealFiles(unittest.TestCase):
    def test_faststart_reaches_the_delivered_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.mp4"
            detailed_source(source, seconds=0.5)

            final = root / "final.mp4"
            media.concat_segments([source], final, final=True)
            self.assertTrue(moov_before_mdat(final), "в финальном файле нет faststart")

            middle = root / "middle.mp4"
            media.concat_segments([source], middle)
            self.assertFalse(
                moov_before_mdat(middle),
                "промежуточный файл не должен тратить проход на перестановку индекса",
            )

    def test_single_segment_still_gets_the_final_profile(self) -> None:
        """Склеивать нечего — но копия унесла бы в прод промежуточный профиль."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.mp4"
            detailed_source(source, seconds=0.5)
            out = root / "one.mp4"
            media.concat_with_transitions([source], out, [0.5], 0.5, final=True)
            self.assertTrue(moov_before_mdat(out))

    def test_three_passes_lose_less_than_the_old_settings(self) -> None:
        """Настоящая цена прежней схемы: три пересжатия подряд.

        Сегмент кадра → сцена → склейка сцен. Раньше каждый проход шёл с
        CRF 20, теперь промежуточные идут с запасом. Сравнение — с исходником.
        """
        old_profile = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.mp4"
            detailed_source(source, seconds=0.5)

            def chain(profile: list[str], tag: str) -> float:
                current = source
                for step in range(3):
                    out = root / f"{tag}_{step}.mp4"
                    reencode(current, out, profile)
                    current = out
                return psnr_against(current, source)

            old_psnr = chain(old_profile, "old")
            new_psnr = chain(media._ENCODE_INTERMEDIATE, "new")
            self.assertGreater(
                new_psnr, old_psnr,
                f"новая схема должна терять меньше: было {old_psnr:.2f} дБ, стало {new_psnr:.2f} дБ",
            )
            print(f"\n  три пересжатия: прежние настройки {old_psnr:.2f} дБ → новые {new_psnr:.2f} дБ")


if __name__ == "__main__":
    unittest.main()
