"""Windows scanner discovery for Unstoppable Invoice Splitter.

Phase 1 deliberately performs discovery only.  Actual acquisition will be added
after we confirm how the installed Canon R40 driver is exposed on the target PC.
"""

import os
import subprocess
import tempfile


class ScannerError(RuntimeError):
    pass


def discover_scanners():
    """Return Windows imaging devices visible through WIA.

    Uses PowerShell/COM so the development build needs no additional Python
    package just to discover the scanner.
    """
    script = r"""
$ErrorActionPreference = 'Stop'
$manager = New-Object -ComObject WIA.DeviceManager
$devices = @()
foreach ($info in $manager.DeviceInfos) {
    if ($info.Type -eq 1) {
        $name = ''
        try { $name = $info.Properties.Item('Name').Value } catch {}
        if ([string]::IsNullOrWhiteSpace($name)) { $name = "Scanner $($info.DeviceID)" }
        $devices += [PSCustomObject]@{
            Name = $name
            DeviceID = $info.DeviceID
        }
    }
}
$devices | ConvertTo-Json -Compress
"""
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ScannerError(f"Could not query Windows scanners: {exc}") from exc

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Unknown WIA error"
        raise ScannerError(f"Windows scanner detection failed: {message}")

    import json
    raw = result.stdout.strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ScannerError(f"Could not read scanner list: {exc}") from exc
    if isinstance(data, dict):
        data = [data]
    return data


def preferred_scanner(devices):
    """Prefer the Canon imageFORMULA R40 when it is present."""
    for device in devices:
        name = str(device.get("Name", "")).lower()
        if "r40" in name or ("canon" in name and "imageformula" in name):
            return device
    return devices[0] if devices else None


def scan_batch(device_id=None, dpi=300, duplex=True, max_pages=200):
    """Scan all pages available in the WIA feeder and return image file paths.

    The files live in a temporary batch directory. The caller owns that
    directory for the lifetime of the imported document.
    """
    batch_dir = tempfile.mkdtemp(prefix="unstoppable_scan_")
    safe_dir = batch_dir.replace("'", "''")
    safe_id = (device_id or "").replace("'", "''")
    duplex_value = 5 if duplex else 1  # feeder + duplex, or feeder only

    script = rf"""
$ErrorActionPreference = 'Stop'
$manager = New-Object -ComObject WIA.DeviceManager
$target = $null
foreach ($info in $manager.DeviceInfos) {{
    if ($info.Type -eq 1) {{
        if ('{safe_id}' -and $info.DeviceID -eq '{safe_id}') {{ $target = $info; break }}
        $name = ''
        try {{ $name = $info.Properties.Item('Name').Value }} catch {{}}
        if (-not $target -and ($name -match 'R40|imageFORMULA')) {{ $target = $info }}
    }}
}}
if (-not $target) {{ throw 'Canon R40 scanner was not found.' }}

$device = $target.Connect()

# Prefer the automatic document feeder and duplex when the driver exposes it.
try {{ $device.Properties.Item('Document Handling Select').Value = {duplex_value} }} catch {{}}
try {{ $device.Properties.Item(3088).Value = {duplex_value} }} catch {{}}

$item = $device.Items.Item(1)
try {{ $item.Properties.Item('Horizontal Resolution').Value = {dpi} }} catch {{}}
try {{ $item.Properties.Item('Vertical Resolution').Value = {dpi} }} catch {{}}
try {{ $item.Properties.Item(6147).Value = {dpi} }} catch {{}}
try {{ $item.Properties.Item(6148).Value = {dpi} }} catch {{}}

$paths = @()
for ($n = 1; $n -le {max_pages}; $n++) {{
    try {{
        $image = $item.Transfer()
        if (-not $image) {{ break }}
        $path = Join-Path '{safe_dir}' ('page_' + $n.ToString('000') + '.bmp')
        $image.SaveFile($path)
        $paths += $path
    }}
    catch {{
        if ($paths.Count -eq 0) {{ throw }}
        break
    }}
}}
$paths | ConvertTo-Json -Compress
"""
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ScannerError(f"Batch scan failed: {exc}") from exc

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Unknown WIA scan error"
        raise ScannerError(f"Batch scan failed: {message}")

    import json
    raw = result.stdout.strip()
    if not raw:
        raise ScannerError("The scanner returned no pages. Check the document feeder.")
    try:
        paths = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ScannerError(f"Could not read scanned page list: {exc}") from exc
    if isinstance(paths, str):
        paths = [paths]
    paths = [path for path in paths if os.path.isfile(path)]
    if not paths:
        raise ScannerError("The scanner did not produce any readable pages.")
    return paths, batch_dir
