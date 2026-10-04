"""Windows scanner discovery for Unstoppable Invoice Splitter.

Phase 1 deliberately performs discovery only.  Actual acquisition will be added
after we confirm how the installed Canon R40 driver is exposed on the target PC.
"""

import subprocess


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
