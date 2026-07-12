import os
import shutil
import subprocess
import tempfile
from pathlib import Path


class OCREngineError(RuntimeError):
    """Raised when Tesseract OCR cannot be configured or executed."""


class OCREngine:
    def __init__(self):
        self.tesseract_path = self._find_tesseract()
        self.tessdata_path = self._find_tessdata(self.tesseract_path)

    @property
    def available(self):
        return bool(self.tesseract_path and self.tessdata_path)

    def diagnostic_text(self):
        return (
            f"Tesseract: {self.tesseract_path or 'Not found'}\n"
            f"Tessdata: {self.tessdata_path or 'Not found'}\n"
            f"English data: "
            f"{'Found' if self.tessdata_path and (Path(self.tessdata_path) / 'eng.traineddata').is_file() else 'Not found'}"
        )

    def read_image(self, image, language="eng"):
        if not self.available:
            raise OCREngineError(
                "Tesseract OCR is unavailable.\n\n" + self.diagnostic_text()
            )

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                temp_path = temp_file.name

            image.save(temp_path, format="PNG")

            command = [
                self.tesseract_path,
                temp_path,
                "stdout",
                "-l",
                language,
                "--tessdata-dir",
                self.tessdata_path,
                "--psm",
                "6",
            ]

            environment = os.environ.copy()
            environment.pop("TESSDATA_PREFIX", None)

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=environment,
                timeout=120,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

            if result.returncode != 0:
                detail = result.stderr.strip() or "Unknown Tesseract error."
                raise OCREngineError(
                    f"OCR failed with exit code {result.returncode}: {detail}\n\n"
                    + self.diagnostic_text()
                )

            return result.stdout.strip()
        except subprocess.TimeoutExpired as error:
            raise OCREngineError("OCR timed out after 120 seconds.") from error
        finally:
            if temp_path:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def _find_tesseract(self):
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            shutil.which("tesseract"),
        ]

        for candidate in candidates:
            if candidate and Path(candidate).is_file():
                return str(Path(candidate))

        return None

    def _find_tessdata(self, tesseract_path):
        candidates = []

        if tesseract_path:
            candidates.append(Path(tesseract_path).parent / "tessdata")

        environment_path = os.environ.get("TESSDATA_PREFIX")
        if environment_path:
            candidates.append(Path(environment_path))

        for candidate in candidates:
            if (candidate / "eng.traineddata").is_file():
                return str(candidate)

        return None
