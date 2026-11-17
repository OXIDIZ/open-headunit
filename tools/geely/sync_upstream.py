#!/usr/bin/env python3
"""Merge the latest stable OHU release locally; the workflow tests it before pushing."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request

UPSTREAM = "andreknieriem/open-headunit"
STATE = Path("geely/upstream.json")
TAG_PATTERN = re.compile(r"v?\.?\d+\.\d+\.\d+\Z")


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()


def stable_tag(release):
    tag = release["tag_name"]
    if release.get("draft") or release.get("prerelease") or not TAG_PATTERN.fullmatch(tag):
        raise ValueError(f"Not a stable OHU release tag: {tag!r}")
    return tag


def choose_stable_release(releases):
    # Some OHU beta releases have prerelease=false, so also inspect the tag itself.
    stable = [r for r in releases if not r.get("draft") and not r.get("prerelease")
              and TAG_PATTERN.fullmatch(r.get("tag_name", ""))]
    if not stable:
        raise RuntimeError("No stable OHU release found")
    return max(stable, key=lambda r: tuple(map(int, r["tag_name"].lstrip("v.").split("."))))


def latest_release():
    request = urllib.request.Request(
        f"https://api.github.com/repos/{UPSTREAM}/releases?per_page=100",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "OXIDIZ-Geely-sync"},
    )
    token = os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return choose_stable_release(json.load(response))


def merge_release(root, upstream_url, tag):
    if not TAG_PATTERN.fullmatch(tag):
        raise ValueError("Invalid release tag")
    if git(root, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("Refusing to sync a working tree with tracked local changes")
    git(root, "fetch", "--no-tags", upstream_url, f"refs/tags/{tag}")
    sha = git(root, "rev-parse", "FETCH_HEAD^{commit}")
    ancestor = subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", sha, "HEAD"])
    if ancestor.returncode not in (0, 1):
        raise RuntimeError("Could not determine release ancestry")
    old_state = root / STATE
    state = {"repository": UPSTREAM, "tag": tag, "commit": sha}
    if ancestor.returncode == 1:
        try:
            git(root, "merge", "--no-ff", "--no-edit", "-m", f"Merge OHU {tag} with Geely adaptations", sha)
        except subprocess.CalledProcessError as exc:
            conflicts = git(root, "diff", "--name-only", "--diff-filter=U")
            git(root, "merge", "--abort")
            raise RuntimeError(f"Upstream merge needs review; nothing was pushed. Conflicts:\n{conflicts}") from exc
    current = json.loads(old_state.read_text()) if old_state.exists() else None
    changed = ancestor.returncode == 1 or current != state
    if current != state:
        old_state.parent.mkdir(parents=True, exist_ok=True)
        old_state.write_text(json.dumps(state, indent=2) + "\n")
        git(root, "add", str(STATE))
        git(root, "commit", "-m", f"Record stable OHU release {tag}")
    return changed, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--always-build", action="store_true")
    args = parser.parse_args()
    tag = stable_tag(latest_release())
    changed, sha = merge_release(args.root, f"https://github.com/{UPSTREAM}.git", tag)
    outputs = f"build_required={str(changed or args.always_build).lower()}\nupstream_tag={tag}\nupstream_sha={sha}\n"
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as handle:
            handle.write(outputs)
    print(outputs, end="")


if __name__ == "__main__":
    main()
