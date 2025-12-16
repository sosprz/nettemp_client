from __future__ import annotations

import re
import shlex
import subprocess
from dataclasses import dataclass


_NETTEMP_CRON_LINE_RE = re.compile(
    r"(?i)\b(nettemp-client|nettemp\.nettemp_client|nettemp_client\.py|nettemp_client)\b"
)


def is_nettemp_cron_line(line: str) -> bool:
    return bool(_NETTEMP_CRON_LINE_RE.search(line))


def is_canonical_nettemp_cron_line(line: str) -> bool:
    # Canonical forms:
    # - python -m nettemp.nettemp_client (recommended)
    # - nettemp-client (console script, common with pipx)
    lowered = line.lower()
    return ("-m nettemp.nettemp_client" in lowered) or ("nettemp-client" in lowered)


def _read_crontab() -> str:
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    except FileNotFoundError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout or ""


def _write_crontab(contents: str) -> None:
    subprocess.run(["crontab", "-"], input=contents, text=True, check=True)


def remove_nettemp_entries(crontab_text: str) -> str:
    lines = []
    for line in (crontab_text or "").splitlines():
        if not line.strip():
            continue
        if is_nettemp_cron_line(line):
            continue
        lines.append(line)
    return "\n".join(lines) + ("\n" if lines else "")


def build_nettemp_reboot_entry(python_cmd: str) -> str:
    py = shlex.quote(python_cmd)
    return (
        "@reboot /bin/sleep 30 && "
        f"NETTEMP_CLIENT_BG=1 {py} -m nettemp.nettemp_client > /dev/null 2>&1 &"
    )


@dataclass(frozen=True)
class CronStatus:
    has_any: bool
    lines: list[str]
    canonical_lines: list[str]
    legacy_lines: list[str]


def get_nettemp_cron_status() -> CronStatus:
    text = _read_crontab()
    lines = [line for line in text.splitlines() if is_nettemp_cron_line(line)]
    canonical_lines = [line for line in lines if is_canonical_nettemp_cron_line(line)]
    legacy_lines = [line for line in lines if line not in canonical_lines]
    return CronStatus(
        has_any=bool(lines),
        lines=lines,
        canonical_lines=canonical_lines,
        legacy_lines=legacy_lines,
    )


def install_or_replace_nettemp_cron(python_cmd: str) -> str:
    """
    Remove any legacy nettemp cron lines and install the canonical module-based entry.

    Returns the line that was installed.
    """
    current = _read_crontab()
    cleaned = remove_nettemp_entries(current)
    entry = build_nettemp_reboot_entry(python_cmd)
    new_contents = cleaned + entry + "\n"
    _write_crontab(new_contents)
    return entry


def remove_all_nettemp_cron() -> bool:
    """Remove any nettemp-related cron lines. Returns True if anything was removed."""
    current = _read_crontab()
    cleaned = remove_nettemp_entries(current)
    changed = cleaned != current
    if changed:
        _write_crontab(cleaned)
    return changed
