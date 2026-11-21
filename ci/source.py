#!/usr/bin/env python3
"""Fetch a fixed School Day source revision into the CI workspace."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tomllib

UPSTREAM = "https://github.com/sqeezy-53/school-day.git"
SHA = re.compile(r"[0-9a-f]{40}")
VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")

def resolve(ref, expected_sha="", official=False):
    tag = ref[1:] if ref.startswith("v") and VERSION.fullmatch(ref[1:]) else ""
    if not tag and not SHA.fullmatch(ref):
        raise ValueError("source must be a complete commit SHA or existing vMAJOR.MINOR.PATCH tag")
    if expected_sha and not SHA.fullmatch(expected_sha):
        raise ValueError("expected_sha must be a complete lowercase SHA")
    if official and (not tag or not expected_sha):
        raise ValueError("signing needs a release tag and a reviewed expected_sha")
    return (f"refs/tags/{ref}" if tag else ref), (expected_sha or (ref if not tag else "")), tag

def git(cwd, *args):
    return subprocess.check_output(["git", "-c", "core.hooksPath=/dev/null", *args], cwd=cwd, text=True).strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", required=True)
    parser.add_argument("--expected", default="")
    parser.add_argument("--platform", choices=("android", "flatpak"), required=True)
    parser.add_argument("--mode", choices=("test", "prepare", "draft"), default="test")
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    ref, expected, version_from_tag = resolve(args.ref, args.expected, args.mode != "test")
    directory = args.directory.resolve()
    directory.mkdir()
    git(directory, "init", "--quiet")
    git(directory, "fetch", "--quiet", "--no-tags", "--depth=1", UPSTREAM, ref)
    commit = git(directory, "rev-parse", "--verify", "FETCH_HEAD^{commit}")
    if expected and commit != expected:
        raise ValueError(f"source resolved to {commit}, expected {expected}")
    git(directory, "checkout", "--quiet", "--detach", commit)
    version = tomllib.loads((directory / "Cargo.toml").read_text())["package"]["version"]
    if not VERSION.fullmatch(version) or (version_from_tag and version != version_from_tag):
        raise ValueError("Cargo.toml version does not match the selected release")
    files = {
        "android": ("android/gradlew", "android/app/build.gradle.kts", "crates/school-day-android/Cargo.toml"),
        "flatpak": ("packaging/build-flatpak.py", "packaging/flatpak/io.github.sqeezy_53.school-day.json"),
    }[args.platform]
    missing = [file for file in files if not (directory / file).is_file()]
    if missing:
        raise ValueError(f"{args.platform} sources are absent in upstream commit {commit}: {', '.join(missing)}")
    if args.platform == "flatpak" and args.mode != "test" and not (directory / "packaging/flatpak/prepare-repository.py").is_file():
        raise ValueError("selected Flatpak source has no signed repository preparation helper")
    metadata = {"repo": "sqeezy-53/school-day", "ref": args.ref, "sha": commit,
                "version": version, "platform": args.platform, "mode": args.mode}
    print(json.dumps(metadata), flush=True)
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a") as f:
            for key in ("ref", "sha", "version"):
                f.write(f"{key}={metadata[key]}\n")

if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as e:
        raise SystemExit(str(e)) from None
