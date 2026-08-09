"""Refuse a replay matrix whose cells do not exist, before spending an hour on it.

Run 31278210299 requested ``macos-14`` with CPython 3.12.13. That combination
does not exist: macOS/arm64 has no 3.12.11 or later in the
``actions/python-versions`` manifest. The runner failed at ``setup-python``
after the matrix had already launched, and the failure was then compounded by a
second, misleading error from the artifact-upload step reporting missing files
that were never produced.

This validates every requested tuple against the live manifest and exits nonzero
before dispatch. A matrix cell that cannot exist should cost seconds, not a
job-hour and a confusing log.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

MANIFEST = "https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json"

#: GitHub runner label -> the manifest's platform/arch pair.
_RUNNER_PLATFORM = {
    "macos-14": ("darwin", "arm64"),
    "macos-14-arm64": ("darwin", "arm64"),
    "macos-13": ("darwin", "x64"),
    "ubuntu-22.04": ("linux", "x64"),
    "ubuntu-24.04": ("linux", "x64"),
    "windows-2022": ("win32", "x64"),
}


def _available() -> dict[str, set[tuple[str, str]]]:
    with urllib.request.urlopen(MANIFEST, timeout=30) as response:
        data = json.loads(response.read())
    out: dict[str, set[tuple[str, str]]] = {}
    for entry in data:
        version = entry["version"]
        if not re.fullmatch(r"\d+\.\d+\.\d+", version):
            continue
        out[version] = {(f["platform"], f.get("arch", "")) for f in entry["files"]}
    return out


def main() -> int:
    scope_path = Path(__file__).resolve().parents[1] / "configs/gate_f_replay_scope.json"
    scope = json.loads(scope_path.read_text())
    runners = scope["runners"]

    available = _available()
    problems: list[str] = []

    for runner in runners:
        os_label, python = runner["os"], runner["python"]
        if re.fullmatch(r"\d+\.\d+", python):
            problems.append(
                f"{os_label} requests floating '{python}'. A confirmatory "
                f"portability gate must pin an exact patch: a floating alias "
                f"silently changes what was measured between runs."
            )
            continue
        platform = _RUNNER_PLATFORM.get(os_label)
        if platform is None:
            problems.append(f"unknown runner label {os_label!r}")
            continue
        if python not in available:
            problems.append(f"{os_label}: CPython {python} is not in the manifest at all")
            continue
        if platform not in available[python]:
            # Sorted by integer patch, not lexically: "3.12.9" sorts above
            # "3.12.10" as a string, and this number goes into an error message
            # a human acts on.
            have = sorted(
                (v for v, plats in available.items()
                 if platform in plats and v.startswith(python.rsplit(".", 1)[0] + ".")),
                key=lambda v: tuple(int(part) for part in v.split(".")),
            )
            problems.append(
                f"{os_label} ({platform[0]}/{platform[1]}): CPython {python} is "
                f"NOT available. Highest available on this platform for that "
                f"minor: {have[-1] if have else 'none'}"
            )

    print(f"validating {len(runners)} runner(s) against the live manifest\n")
    for runner in runners:
        print(f"  {runner['os']:16s} py{runner['python']:9s} {runner.get('role','')}")
    if problems:
        print("\nMATRIX INVALID -- not dispatching:\n")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nall requested cells exist.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
