# -*- coding: utf-8 -*-
"""
Cleep Pico firmware package contract.

A firmware package is a pair of sidecar files (no manifest inside the zip)::

    <id>.zip
    <id>.manifest

In a cleepapp source / archive they live under ``firmwares/``.
On device they are installed under ``APP_FIRMWARE_PATH`` (see CleepModule).

Manifest schema version 1 (JSON object)::

    {
        "version": 1,
        "id": "myapp_pico_w_v1.2.0",
        "name": "MyApp Pico",
        "app": "myapp",
        "firmware_version": "1.2.0",
        "date": "2026-11-09",
        "hash": "sha256:<hex>",
        "targets": ["pico_w"],
        "kind": "native" | "micropython-runtime" | "micropython-app",
        "requires_bootsel": true,
        "description": "optional",
        "sources": {                    # optional
            "language": "c" | "python",
            "entry": "files/main.py"    # path inside the zip
        }
    }

Zip content rules by ``kind``:
  - native / micropython-runtime: require ``payload.uf2`` at zip root
  - micropython-app: require ``files/`` with at least one ``.py``;
    optional ``payload.uf2`` (runtime) at zip root
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import zipfile
from typing import Any

SUPPORTED_VERSION = 1

KIND_NATIVE = "native"
KIND_MICROPYTHON_RUNTIME = "micropython-runtime"
KIND_MICROPYTHON_APP = "micropython-app"
ALLOWED_KINDS = frozenset(
    {KIND_NATIVE, KIND_MICROPYTHON_RUNTIME, KIND_MICROPYTHON_APP}
)

ALLOWED_TARGETS = frozenset(
    {
        "pico",
        "pico_h",
        "pico_w",
        "pico2",
        "pico2_h",
        "pico2_w",
    }
)

ALLOWED_SOURCE_LANGUAGES = frozenset({"c", "python"})

MANIFEST_EXT = ".manifest"
ZIP_EXT = ".zip"
PAYLOAD_UF2 = "payload.uf2"
FILES_DIR = "files/"

# id: basename without extension (may include version dots, e.g. demo_pico_w_v1.0.0)
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,127}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_APP_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_FW_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


class FirmwareManifestError(Exception):
    """Invalid firmware manifest or package pair."""


def compute_zip_hash(zip_path: str) -> str:
    """
    Return ``sha256:<hex>`` for the zip file on disk.

    Args:
        zip_path (str): path to the firmware zip

    Returns:
        str: canonical hash string
    """
    digest = hashlib.sha256()
    with open(zip_path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return "sha256:%s" % digest.hexdigest()


def manifest_path_for_zip(zip_path: str) -> str:
    """
    Return the sidecar manifest path for a firmware zip path.
    """
    if not zip_path.endswith(ZIP_EXT):
        raise FirmwareManifestError('Firmware zip must end with "%s"' % ZIP_EXT)
    return zip_path[: -len(ZIP_EXT)] + MANIFEST_EXT


def zip_path_for_manifest(manifest_path: str) -> str:
    """
    Return the zip path for a sidecar manifest path.
    """
    if not manifest_path.endswith(MANIFEST_EXT):
        raise FirmwareManifestError(
            'Firmware manifest must end with "%s"' % MANIFEST_EXT
        )
    return manifest_path[: -len(MANIFEST_EXT)] + ZIP_EXT


def load_manifest(manifest_path: str) -> dict[str, Any]:
    """
    Load and structurally validate a sidecar ``.manifest`` file.

    Does not verify the zip hash (use :func:`validate_firmware_pair`).

    Args:
        manifest_path (str): path to ``.manifest``

    Returns:
        dict: parsed manifest

    Raises:
        FirmwareManifestError: invalid JSON or schema
    """
    if not os.path.isfile(manifest_path):
        raise FirmwareManifestError('Manifest not found: "%s"' % manifest_path)
    try:
        with open(manifest_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FirmwareManifestError(
            'Unable to read manifest "%s": %s' % (manifest_path, error)
        ) from error

    if not isinstance(data, dict):
        raise FirmwareManifestError("Manifest root must be a JSON object")

    _validate_manifest_fields(data, os.path.basename(manifest_path))
    return data


def _require_str(data: dict, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise FirmwareManifestError('Manifest field "%s" must be a non-empty string' % key)
    return value.strip()


def _validate_manifest_fields(data: dict[str, Any], basename: str) -> None:
    version = data.get("version")
    if version != SUPPORTED_VERSION:
        raise FirmwareManifestError(
            'Unsupported manifest version %r (expected %s)' % (version, SUPPORTED_VERSION)
        )

    firmware_id = _require_str(data, "id")
    if not _ID_RE.match(firmware_id):
        raise FirmwareManifestError('Invalid manifest id "%s"' % firmware_id)

    expected_basename = firmware_id + MANIFEST_EXT
    if basename != expected_basename:
        raise FirmwareManifestError(
            'Manifest filename "%s" must match id ("%s")'
            % (basename, expected_basename)
        )

    _require_str(data, "name")

    app = _require_str(data, "app")
    if not _APP_RE.match(app):
        raise FirmwareManifestError('Invalid manifest app "%s"' % app)

    firmware_version = _require_str(data, "firmware_version")
    if not _FW_VERSION_RE.match(firmware_version):
        raise FirmwareManifestError(
            'Invalid firmware_version "%s" (expected X.Y.Z)' % firmware_version
        )

    date = _require_str(data, "date")
    if not _DATE_RE.match(date):
        raise FirmwareManifestError('Invalid date "%s" (expected YYYY-MM-DD)' % date)

    digest = _require_str(data, "hash")
    if not _HASH_RE.match(digest):
        raise FirmwareManifestError(
            'Invalid hash "%s" (expected sha256:<64 hex chars>)' % digest
        )

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise FirmwareManifestError('Manifest field "targets" must be a non-empty list')
    for target in targets:
        if not isinstance(target, str) or target not in ALLOWED_TARGETS:
            raise FirmwareManifestError(
                'Invalid target %r (allowed: %s)'
                % (target, ", ".join(sorted(ALLOWED_TARGETS)))
            )

    kind = _require_str(data, "kind")
    if kind not in ALLOWED_KINDS:
        raise FirmwareManifestError(
            'Invalid kind "%s" (allowed: %s)' % (kind, ", ".join(sorted(ALLOWED_KINDS)))
        )

    requires_bootsel = data.get("requires_bootsel")
    if not isinstance(requires_bootsel, bool):
        raise FirmwareManifestError('Manifest field "requires_bootsel" must be a boolean')

    if "description" in data and data["description"] is not None:
        if not isinstance(data["description"], str):
            raise FirmwareManifestError('Manifest field "description" must be a string')

    if "sources" in data and data["sources"] is not None:
        sources = data["sources"]
        if not isinstance(sources, dict):
            raise FirmwareManifestError('Manifest field "sources" must be an object')
        language = sources.get("language")
        if language not in ALLOWED_SOURCE_LANGUAGES:
            raise FirmwareManifestError(
                'Invalid sources.language %r (allowed: %s)'
                % (language, ", ".join(sorted(ALLOWED_SOURCE_LANGUAGES)))
            )
        entry = sources.get("entry")
        if not isinstance(entry, str) or not entry.strip():
            raise FirmwareManifestError('sources.entry must be a non-empty string')
        entry = entry.strip().replace("\\", "/")
        if entry.startswith("/") or ".." in entry.split("/"):
            raise FirmwareManifestError('sources.entry must be a relative zip path')
        sources["entry"] = entry


def validate_zip_contents(zip_path: str, kind: str) -> None:
    """
    Validate firmware zip internal layout for the given kind.

    Args:
        zip_path (str): path to zip
        kind (str): manifest kind

    Raises:
        FirmwareManifestError: invalid archive or layout
    """
    if kind not in ALLOWED_KINDS:
        raise FirmwareManifestError('Invalid kind "%s"' % kind)
    if not os.path.isfile(zip_path):
        raise FirmwareManifestError('Firmware zip not found: "%s"' % zip_path)

    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            names = [name.replace("\\", "/") for name in archive.namelist()]
    except zipfile.BadZipFile as error:
        raise FirmwareManifestError(
            'Invalid zip archive "%s": %s' % (zip_path, error)
        ) from error

    # Reject absolute / traversal paths
    for name in names:
        if name.startswith("/") or name.startswith("../") or "/../" in name:
            raise FirmwareManifestError(
                'Unsafe path in firmware zip: "%s"' % name
            )

    has_uf2 = PAYLOAD_UF2 in names
    py_files = [
        name
        for name in names
        if name.startswith(FILES_DIR)
        and not name.endswith("/")
        and name.lower().endswith(".py")
    ]

    if kind in {KIND_NATIVE, KIND_MICROPYTHON_RUNTIME}:
        if not has_uf2:
            raise FirmwareManifestError(
                'Firmware kind "%s" requires "%s" at zip root' % (kind, PAYLOAD_UF2)
            )
    elif kind == KIND_MICROPYTHON_APP:
        if not py_files:
            raise FirmwareManifestError(
                'Firmware kind "%s" requires at least one .py under "%s"'
                % (kind, FILES_DIR)
            )


def validate_firmware_pair(zip_path: str, manifest_path: str | None = None) -> dict[str, Any]:
    """
    Validate a zip + sidecar manifest pair (schema, hash, zip contents).

    Args:
        zip_path (str): path to ``.zip``
        manifest_path (str): optional path to ``.manifest`` (default: sidecar next to zip)

    Returns:
        dict: loaded manifest

    Raises:
        FirmwareManifestError: validation failure
    """
    if manifest_path is None:
        manifest_path = manifest_path_for_zip(zip_path)

    if not os.path.isfile(zip_path):
        raise FirmwareManifestError('Firmware zip not found: "%s"' % zip_path)

    manifest = load_manifest(manifest_path)

    expected_zip = zip_path_for_manifest(manifest_path)
    if os.path.abspath(zip_path) != os.path.abspath(expected_zip):
        raise FirmwareManifestError(
            'Zip/manifest basename mismatch ("%s" vs "%s")'
            % (os.path.basename(zip_path), os.path.basename(manifest_path))
        )

    if manifest["id"] + ZIP_EXT != os.path.basename(zip_path):
        raise FirmwareManifestError(
            'Zip filename "%s" must match manifest id ("%s%s")'
            % (os.path.basename(zip_path), manifest["id"], ZIP_EXT)
        )

    actual_hash = compute_zip_hash(zip_path)
    if actual_hash != manifest["hash"]:
        raise FirmwareManifestError(
            'Firmware hash mismatch for "%s": manifest has %s, file is %s'
            % (os.path.basename(zip_path), manifest["hash"], actual_hash)
        )

    validate_zip_contents(zip_path, manifest["kind"])

    if manifest.get("sources"):
        entry = manifest["sources"]["entry"]
        with zipfile.ZipFile(zip_path, "r") as archive:
            names = {name.replace("\\", "/") for name in archive.namelist()}
        if entry not in names:
            raise FirmwareManifestError(
                'sources.entry "%s" not found inside firmware zip' % entry
            )

    return manifest


def scan_firmwares_dir(firmwares_dir: str) -> list[dict[str, Any]]:
    """
    Scan a ``firmwares/`` directory for valid zip+manifest pairs.

    Missing directory is valid (empty list). Orphan zip/manifest files are errors.

    Args:
        firmwares_dir (str): path to firmwares directory

    Returns:
        list[dict]: each item ``{zip, manifest, data}`` sorted by id

    Raises:
        FirmwareManifestError: orphan files or invalid pairs
    """
    if not os.path.isdir(firmwares_dir):
        return []

    zips: set[str] = set()
    manifests: set[str] = set()
    for filename in os.listdir(firmwares_dir):
        fullpath = os.path.join(firmwares_dir, filename)
        if not os.path.isfile(fullpath):
            continue
        if filename.endswith(ZIP_EXT):
            zips.add(filename[: -len(ZIP_EXT)])
        elif filename.endswith(MANIFEST_EXT):
            manifests.add(filename[: -len(MANIFEST_EXT)])
        elif filename == ".gitkeep":
            continue
        else:
            raise FirmwareManifestError(
                'Unexpected file in firmwares/: "%s" (only .zip/.manifest allowed)'
                % filename
            )

    orphans_zip = sorted(zips - manifests)
    orphans_manifest = sorted(manifests - zips)
    if orphans_zip:
        raise FirmwareManifestError(
            "Firmware zip without sidecar manifest: %s"
            % ", ".join("%s%s" % (name, ZIP_EXT) for name in orphans_zip)
        )
    if orphans_manifest:
        raise FirmwareManifestError(
            "Firmware manifest without zip: %s"
            % ", ".join("%s%s" % (name, MANIFEST_EXT) for name in orphans_manifest)
        )

    results = []
    for firmware_id in sorted(zips):
        zip_path = os.path.join(firmwares_dir, firmware_id + ZIP_EXT)
        manifest_path = os.path.join(firmwares_dir, firmware_id + MANIFEST_EXT)
        data = validate_firmware_pair(zip_path, manifest_path)
        results.append(
            {
                "id": firmware_id,
                "zip": zip_path,
                "manifest": manifest_path,
                "data": data,
            }
        )
    return results


def build_manifest(
    *,
    firmware_id: str,
    name: str,
    app: str,
    firmware_version: str,
    date: str,
    zip_path: str,
    targets: list[str],
    kind: str,
    requires_bootsel: bool = True,
    description: str | None = None,
    sources: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Build a manifest dict (hash computed from ``zip_path``). Useful for package tooling.
    """
    manifest: dict[str, Any] = {
        "version": SUPPORTED_VERSION,
        "id": firmware_id,
        "name": name,
        "app": app,
        "firmware_version": firmware_version,
        "date": date,
        "hash": compute_zip_hash(zip_path),
        "targets": list(targets),
        "kind": kind,
        "requires_bootsel": requires_bootsel,
    }
    if description is not None:
        manifest["description"] = description
    if sources is not None:
        manifest["sources"] = dict(sources)
    # Validate shape before returning
    _validate_manifest_fields(manifest, firmware_id + MANIFEST_EXT)
    validate_zip_contents(zip_path, kind)
    if sources and sources.get("entry"):
        with zipfile.ZipFile(zip_path, "r") as archive:
            names = {name.replace("\\", "/") for name in archive.namelist()}
        if sources["entry"] not in names:
            raise FirmwareManifestError(
                'sources.entry "%s" not found inside firmware zip' % sources["entry"]
            )
    return manifest


def write_manifest(manifest: dict[str, Any], manifest_path: str) -> None:
    """
    Write a manifest JSON file (UTF-8, indented).
    """
    _validate_manifest_fields(manifest, os.path.basename(manifest_path))
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=4, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
