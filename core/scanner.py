"""TWAIN scanner support for Unstoppable Invoice Splitter.

The Canon imageFORMULA R40 is acquired through its native 64-bit TWAIN driver
using the open-source TwainSave command-line bridge. WIA remains useful for
basic Windows discovery, but is intentionally not used for ADF acquisition.
"""

import os
import subprocess


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
    lines = list_twain_sources()
    # TwainSave's device-list output can contain labels around the product name.
    # Prefer any line containing R40; selectbyname also accepts the product name
    # reported by the TWAIN source.
    for line in lines:
        if "r40" in line.lower():
            # Common outputs are either the raw product name or "N: Product".
            candidate = line.split(":", 1)[-1].strip()
            return candidate.strip('"')
    raise ScannerError(
        "The Canon R40 TWAIN source was not found. Installed TWAIN sources: "
        + (", ".join(lines) if lines else "none")
    )


def scan_batch(output_path, dpi=300, duplex=True):
    """Acquire the complete Canon R40 ADF into one multipage PDF."""
    exe = _find_twainsave()
    if not exe:
        raise ScannerError(
            "TWAIN support is not installed yet. Run setup_twain.ps1 once, then restart the app."
        )

    # For the first TWAIN acquisition, let the TWAIN Source Manager present
    # its native source picker. This avoids guessing/parsing a product name
    # from TwainSave's console output. Once Canon R40 acquisition is proven,
    # we can persist/select that exact source automatically.
    source = "Canon R40 (TWAIN)"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    args = [
        exe,
        "--selectbydialog",
        "--filename", output_path,
        "--filetype", "pdf",
        "--multipage",
        "--autofeed",
        "--resolution", str(dpi),
        "--color", "2",
        "--papersize", "letter",
        "--noui",
        "--numpages", "0",
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
    if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
        raise ScannerError(
            "The Canon R40 finished without creating a PDF. "
            + (details if details else "Check that pages are loaded in the feeder.")
        )
    return output_path, source
