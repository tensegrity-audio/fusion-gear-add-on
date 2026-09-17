#!/usr/bin/env python3
"""Build a reproducible, self-contained Gear Studio source/install ZIP.

Standard library only. --check inspects the release tree without writing a ZIP.
SOURCE_DATE_EPOCH can supply the timestamp; its default is fixed for reproducibility.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time
import zipfile


ROOT = Path(__file__).resolve().parents[1]
TOP_FILES = (
    "README.md", "START_HERE.html", "LICENSE", "CONTRACT.md", ".gitignore", ".gitattributes",
    "CHANGELOG.md", "CONTRIBUTING.md", "package.json", "package-lock.json",
    "install_windows.ps1", "install_macos.command",
)
TOP_DIRS = ("GearStudio", "docs", "tests", "tools")
REQUIRED = (
    "GearStudio/GearStudio.py", "GearStudio/GearStudio.manifest",
    "GearStudio/fusion/builder.py", "GearStudio/fusion/history.py",
    "GearStudio/resources/16x16.svg", "GearStudio/resources/32x32.svg", "GearStudio/fusion/controller.py",
    "GearStudio/fusion/document.py", "GearStudio/core/catalog.py",
    "GearStudio/core/validation.py", "GearStudio/core/profiles.py",
    "GearStudio/core/storage.py", "GearStudio/core/templates.py", "GearStudio/ui/index.html",
    "GearStudio/vendor/study_gears/LICENSE.txt",
    "GearStudio/vendor/study_gears/lib/fusion_helper/LICENSE.txt",
    "GearStudio/vendor/study_gears/UPSTREAM.md",
    "README.md", "START_HERE.html", "GearStudio/ui/tokens.css", "LICENSE", "docs/INSTALL.md", "docs/ACCEPTANCE.md",
    "docs/ARCHITECTURE.md", "install_windows.ps1", "install_macos.command",
)
EXCLUDED_DIRS = {
    "__pycache__", ".git", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".venv", "venv", "node_modules", "dist", "artifacts",
}
EXCLUDED_NAMES = {".DS_Store", "Thumbs.db"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp"}


def release_files():
    """Select tracked deliverable categories; never sweep arbitrary scratch files."""
    candidates = [ROOT / name for name in TOP_FILES if (ROOT / name).is_file()]
    for folder in TOP_DIRS:
        path = ROOT / folder
        if not path.is_dir():
            raise ValueError("Missing release directory: " + folder)
        candidates.extend(path.rglob("*"))
    result = {}
    for path in candidates:
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if path.name in EXCLUDED_NAMES or path.suffix in EXCLUDED_SUFFIXES:
            continue
        if path.is_symlink():
            raise ValueError("Release symlinks are not supported: " + relative.as_posix())
        if path.is_file():
            result[relative.as_posix()] = path
    return dict(sorted(result.items()))


def inspect_release(files):
    missing = [name for name in REQUIRED if name not in files]
    if missing:
        raise ValueError("Missing required release files: " + ", ".join(missing))
    manifest = json.loads(files["GearStudio/GearStudio.manifest"].read_text(encoding="utf-8"))
    if manifest.get("type") != "addin":
        raise ValueError("Fusion manifest type must be 'addin'.")
    version = str(manifest.get("version", "0.1.0"))
    if not version or any(char not in "0123456789.-abcdefghijklmnopqrstuvwxyz" for char in version.lower()):
        raise ValueError("Manifest version is not a safe release filename component.")
    if not any(name.startswith("tests/test_") and name.endswith(".py") for name in files):
        raise ValueError("Release must include source tests.")
    return version


def zip_timestamp():
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "1767225600"))
    # ZIP DOS timestamps have a 1980 lower bound and a 2107 upper bound.
    epoch = min(max(epoch, 315532800), 4354819198)
    stamp = time.gmtime(epoch)
    return stamp[:5] + (stamp.tm_sec // 2 * 2,)


def make_info(name, timestamp):
    info = zipfile.ZipInfo(name, timestamp)
    info.create_system = 3
    info.compress_type = zipfile.ZIP_DEFLATED
    mode = 0o755 if name.endswith(".command") else 0o644
    info.external_attr = (stat.S_IFREG | mode) << 16
    return info


def build_zip(files, output):
    if output.suffix.lower() != ".zip":
        raise ValueError("Output filename must end in .zip.")
    if any(output == path.resolve() for path in files.values()):
        raise ValueError("Output would overwrite a release source file.")
    output.parent.mkdir(parents=True, exist_ok=True)
    timestamp = zip_timestamp()
    entries = {name: path.read_bytes() for name, path in files.items()}
    checksums = "".join(hashlib.sha256(data).hexdigest() + "  " + name + "\n"
                        for name, data in entries.items())
    entries["MANIFEST.sha256"] = checksums.encode("utf-8")
    temporary = output.with_name(output.name + ".tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=9, strict_timestamps=True) as archive:
            for name, data in sorted(entries.items()):
                archive.writestr(make_info(name, timestamp), data, compresslevel=9)
        with zipfile.ZipFile(temporary) as archive:
            broken = archive.testzip()
            if broken:
                raise ValueError("Archive verification failed: " + broken)
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix + ".sha256").write_text(
        digest + "  " + output.name + "\n", encoding="utf-8", newline="\n")
    print(str(output))
    print("SHA-256 " + digest)
    print("Packaged %d files plus MANIFEST.sha256." % len(files))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate the file set without writing an archive.")
    parser.add_argument("--output", type=Path, help="ZIP path (default: dist/GearStudio-<version>.zip).")
    args = parser.parse_args()
    try:
        files = release_files()
        version = inspect_release(files)
        if args.check:
            print("Release file check passed: %d files, version %s. Native Fusion acceptance is separate." % (len(files), version))
            return 0
        output = (args.output or ROOT / "dist" / ("GearStudio-%s.zip" % version)).resolve()
        build_zip(files, output)
        return 0
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print("Packaging failed: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
