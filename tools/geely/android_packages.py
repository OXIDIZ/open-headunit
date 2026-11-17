#!/usr/bin/env python3
"""Use OHU's own SDK/NDK/CMake pins after an upstream merge."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
source = (root / "app/build.gradle.kts").read_text()
patterns = {
    "platforms": r"compileSdk\s*=\s*(\d+)",
    "ndk": r'ndkVersion\s*=\s*"([\d.]+)"',
    "cmake": r'version\s*=\s*"([\d.]+)"',
}
for package, pattern in patterns.items():
    match = re.search(pattern, source)
    if not match:
        raise SystemExit(f"Cannot read upstream {package} pin; review app/build.gradle.kts")
    version = f"android-{match[1]}" if package == "platforms" else match[1]
    print(f"{package};{version}")
# Retain a fixed inspector for verify_apk.py even if OHU raises its compile SDK.
print("build-tools;36.0.0")
