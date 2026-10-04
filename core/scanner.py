"""TWAIN scanner support for Unstoppable Invoice Splitter.

The Canon imageFORMULA R40 is acquired through its native 64-bit TWAIN driver
using the open-source TwainSave command-line bridge. WIA remains useful for
basic Windows discovery, but is intentionally not used for ADF acquisition.
"""

import os
import subprocess
import tempfile
import glob


class ScannerError(RuntimeError):
    pass


def _project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _find_twainsave():
    roots = [
        os.path.join(_project_root(), "tools", "twainsave"),
        os.path.join(_project_root(), "twainsave"),
    ]
    for root in roots:
        if not os.path.isdir(root):
            continue
        for folder, _, files in os.walk(root):
            for name in files:
                if name.lower() in ("twainsave64.exe", "twainsave-opensource.exe"):
                    return os.path.join(folder, name)
    return None


def twain_ready():
    return _find_twainsave() is not None


def list_twain_sources():
    exe = _find_twainsave()
    if not exe:
        raise ScannerError(
            "TWAIN support is not installed yet. Run setup_twain.ps1 once, then restart the app."
        )
    result = subprocess.run(
        [exe, "--devicelist"],
        cwd=os.path.dirname(exe),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    if result.returncode != 0:
        raise ScannerError(f"Could not list TWAIN scanners: {output or 'unknown error'}")
    return [line.strip() for line in output.splitlines() if line.strip()]


def _canon_r40_source():
    # The installed Canon 64-bit data source is R40.ds. Canon exposes the
    # product name as "R40" to TWAIN, so select it directly and avoid the
    # source-selection dialog on every scan.
    return "R40"


def scan_batch(dpi=300, duplex=True):
    """Acquire the complete Canon R40 ADF as individual page images.\n\n    Image-quality controls are intentionally left to the Canon TWAIN driver\n    while we tune the R40 profile; the app only requests resolution, feeder,\n    and duplex. This avoids overriding Canon image processing with generic\n    TWAIN defaults.

    Individual files are deliberate: some document TWAIN sources successfully
    feed an entire batch but do not finalize a multipage PDF correctly through
    generic TWAIN. The app combines the returned pages itself.
    """
    exe = _find_twainsave()
    if not exe:
        raise ScannerError(
            "TWAIN support is not installed yet. Run setup_twain.ps1 once, then restart the app."
        )

    batch_dir = tempfile.mkdtemp(prefix="unstoppable_twain_")
    seed = os.path.join(batch_dir, "page.bmp")
    source = "Canon R40 (TWAIN)"

    args = [
        exe,
        "--selectbyname", _canon_r40_source(),
        "--filename", seed,
        "--filetype", "bmp",
        "--autofeed",
        "--resolution", str(dpi),
        "--numpages", "0",
        "--useinc",
        "--incvalue", "1",
        "--overwritemode", "1",
        "--nopause",
    ]
    if duplex:
        args.append("--duplex")

    try:
        result = subprocess.run(
            args,
            cwd=os.path.dirname(exe),
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ScannerError("TWAIN scan timed out before the feeder completed.") from exc
    except OSError as exc:
        raise ScannerError(f"Could not start TWAIN scanning: {exc}") from exc

    details = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    if result.returncode != 0:
        raise ScannerError(f"TWAIN batch scan failed: {details or 'unknown error'}")

    paths = sorted(glob.glob(os.path.join(batch_dir, "*.bmp")))
    if not paths:
        raise ScannerError(
            "The Canon R40 finished without returning page images. "
            + (details if details else "Check that pages are loaded in the feeder.")
        )
    return paths, batch_dir, source

