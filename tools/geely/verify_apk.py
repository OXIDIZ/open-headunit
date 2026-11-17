#!/usr/bin/env python3
"""Check the packaged application, including its merged manifest and signing status."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile

ANDROID = "{http://schemas.android.com/apk/res/android}"
ECARX = {"com.ecarx.media.action.KEY_EVENT", "com.ecarx.intent.action.MEDIA_BUTTON"}


def run(*args):
    return subprocess.run([str(a) for a in args], check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def verify(apk, sdk, require_signature=False):
    build_tools = sdk / "build-tools/36.0.0"
    badging = run(build_tools / "aapt2", "dump", "badging", apk)
    resources = run(build_tools / "aapt2", "dump", "resources", apk)
    assert "drawable/geely_connection_artwork" in resources, "Default GEELY connection image is missing"
    assert "layout/geely_loading_artwork" in resources, "Default connection image layout is missing"
    manifest = ET.fromstring(run(sdk / "cmdline-tools/latest/bin/apkanalyzer", "manifest", "print", apk))
    assert manifest.get("package") == "com.geely.headunitrevived", "Wrong application ID"
    version = manifest.get(ANDROID + "versionName")
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), f"Expected the unmodified OHU version: {version}"
    build_file = (Path(__file__).resolve().parents[2] / "app/build.gradle.kts").read_text()
    expected_version = re.search(r'versionName\s*=\s*"([^"$]+)"', build_file).group(1)
    expected_code = re.search(r'versionCode\s*=\s*(\d+)', build_file).group(1)
    assert version == expected_version, f"APK version differs from OHU: {version} != {expected_version}"
    assert manifest.get(ANDROID + "versionCode") == expected_code, "APK versionCode differs from OHU"
    assert "application-label:'Android Auto'" in badging, "Wrong launcher label"
    for label in re.findall(r"application-label(?:-[^:]+)?:'([^']*)'", badging):
        assert label == "Android Auto", f"Unexpected localized launcher label: {label}"
    permissions = {e.get(ANDROID + "name") for e in manifest.findall("uses-permission")}
    assert "android.permission.TURN_SCREEN_ON" not in permissions
    assert not any("NAVIGATION_UPDATE" in e.get(ANDROID + "name", "") for e in manifest.findall("permission"))
    application = manifest.find("application")
    receivers = [e for e in application.findall("receiver") if e.get(ANDROID + "name", "").endswith(".CarKeyBroadcastReceiver")]
    assert len(receivers) == 1
    actions = {e.get(ANDROID + "name") for e in receivers[0].findall("intent-filter/action")}
    assert actions == ECARX, f"Unexpected OEM receiver actions: {actions}"
    for provider in application.findall("provider"):
        assert provider.get(ANDROID + "authorities", "").startswith("com.geely.headunitrevived."), "Provider ID still belongs to upstream"
    locales_match = re.search(r"^locales:(.*)$", badging, re.MULTILINE)
    locales = re.findall(r"'([^']+)'", locales_match.group(1)) if locales_match else []
    assert "ru" in locales and all(x in {"--_--", "en", "ru"} or x.startswith("en-") for x in locales), f"Unexpected locales: {locales}"
    with zipfile.ZipFile(apk) as archive:
        assert archive.testzip() is None, "Broken APK ZIP"
        artwork = (Path(__file__).resolve().parents[2] /
                   "app/src/main/res/drawable-nodpi-v18/geely_launcher_artwork.webp").read_bytes()
        assert any(archive.read(n) == artwork for n in archive.namelist() if n.endswith(".webp")), \
            "The supplied launcher artwork is missing or has changed"
        abis = {n.split('/')[1] for n in archive.namelist() if n.startswith('lib/')}
        assert abis == {"armeabi-v7a", "arm64-v8a", "x86", "x86_64"}, f"Missing ABI: {abis}"
    if require_signature:
        run(build_tools / "apksigner", "verify", "--verbose", apk)
    return {"apk": str(apk), "version": version, "package": manifest.get("package"), "label": "Android Auto", "locales": locales, "signature_required": require_signature}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--sdk", type=Path, default=Path(os.environ.get("ANDROID_HOME", os.environ.get("ANDROID_SDK_ROOT", "/invalid-sdk"))))
    parser.add_argument("--require-signature", action="store_true")
    args = parser.parse_args()
    result = verify(args.apk, args.sdk, args.require_signature)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as handle:
            handle.write(f"version={result['version']}\n")


if __name__ == "__main__":
    main()
