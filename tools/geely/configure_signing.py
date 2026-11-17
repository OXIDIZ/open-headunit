#!/usr/bin/env python3
"""Read the private GEELY_SIGNING Actions secret without writing its values to logs."""
import base64
import json
import os
from pathlib import Path


def escape_property(value):
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r").replace(" ", "\\ ")


def main():
    root = Path(__file__).resolve().parents[2]
    raw = os.environ.get("GEELY_SIGNING", "")
    configured = bool(raw.strip())
    if configured:
        data = json.loads(raw)
        key = root / ".geely-release.jks"
        key.write_bytes(base64.b64decode(data["keystore_base64"], validate=True))
        key.chmod(0o600)
        values = {"storeFile": "../.geely-release.jks", "storePassword": data["store_password"], "keyAlias": data["key_alias"], "keyPassword": data["key_password"]}
        properties = root / "key.properties"
        properties.write_text("".join(f"{k}={escape_property(v)}\n" for k, v in values.items()))
        properties.chmod(0o600)
        print("Persistent fork signing is configured.")
    else:
        print("GEELY_SIGNING is not set: build an unsigned artifact; do not publish an installable release.")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as handle:
            handle.write(f"configured={str(configured).lower()}\n")


if __name__ == "__main__":
    main()
