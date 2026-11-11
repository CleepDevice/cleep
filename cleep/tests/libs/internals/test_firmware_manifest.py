# -*- coding: utf-8 -*-

import json
import os
import sys
import tempfile
import unittest
import zipfile

# Allow running this file without the full pytest/gevent test harness.
_CLEEP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if _CLEEP_ROOT not in sys.path:
    sys.path.insert(0, _CLEEP_ROOT)

from cleep.libs.internals.firmware_manifest import (  # noqa: E402
    KIND_MICROPYTHON_APP,
    KIND_NATIVE,
    FirmwareManifestError,
    build_manifest,
    compute_zip_hash,
    load_manifest,
    scan_firmwares_dir,
    validate_firmware_pair,
    write_manifest,
)


class FirmwareManifestTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = self._tmpdir.name

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write_zip(self, path, entries):
        with zipfile.ZipFile(path, "w") as archive:
            for name, content in entries.items():
                archive.writestr(name, content)

    def _valid_native_pair(self, firmware_id="demo_pico_w_v1.0.0"):
        zip_path = os.path.join(self.root, firmware_id + ".zip")
        self._write_zip(zip_path, {"payload.uf2": b"UF2fake"})
        manifest = build_manifest(
            firmware_id=firmware_id,
            name="Demo",
            app="demo",
            firmware_version="1.0.0",
            date="2026-11-09",
            zip_path=zip_path,
            targets=["pico_w"],
            kind=KIND_NATIVE,
        )
        manifest_path = os.path.join(self.root, firmware_id + ".manifest")
        write_manifest(manifest, manifest_path)
        return zip_path, manifest_path, manifest

    def test_compute_zip_hash_stable(self):
        zip_path = os.path.join(self.root, "a.zip")
        self._write_zip(zip_path, {"payload.uf2": b"x"})
        self.assertEqual(compute_zip_hash(zip_path), compute_zip_hash(zip_path))
        self.assertTrue(compute_zip_hash(zip_path).startswith("sha256:"))

    def test_validate_native_pair_ok(self):
        zip_path, manifest_path, manifest = self._valid_native_pair()
        loaded = validate_firmware_pair(zip_path, manifest_path)
        self.assertEqual(loaded["id"], manifest["id"])
        self.assertEqual(loaded["hash"], compute_zip_hash(zip_path))

    def test_hash_mismatch(self):
        zip_path, manifest_path, manifest = self._valid_native_pair()
        manifest["hash"] = "sha256:" + ("0" * 64)
        write_manifest(manifest, manifest_path)
        with self.assertRaises(FirmwareManifestError) as ctx:
            validate_firmware_pair(zip_path, manifest_path)
        self.assertIn("hash mismatch", str(ctx.exception))

    def test_missing_uf2_for_native(self):
        zip_path = os.path.join(self.root, "bad_pico_v1.0.0.zip")
        self._write_zip(zip_path, {"readme.txt": b"no"})
        with self.assertRaises(FirmwareManifestError):
            build_manifest(
                firmware_id="bad_pico_v1.0.0",
                name="Bad",
                app="bad",
                firmware_version="1.0.0",
                date="2026-11-09",
                zip_path=zip_path,
                targets=["pico"],
                kind=KIND_NATIVE,
            )

    def test_micropython_app_requires_py(self):
        zip_path = os.path.join(self.root, "mpy_pico_w_v1.0.0.zip")
        self._write_zip(
            zip_path,
            {
                "files/main.py": b"print(1)\n",
                "files/lib/helper.py": b"x=1\n",
            },
        )
        manifest = build_manifest(
            firmware_id="mpy_pico_w_v1.0.0",
            name="MPY",
            app="mpy",
            firmware_version="1.0.0",
            date="2026-11-09",
            zip_path=zip_path,
            targets=["pico_w"],
            kind=KIND_MICROPYTHON_APP,
            requires_bootsel=False,
            sources={"language": "python", "entry": "files/main.py"},
        )
        manifest_path = os.path.join(self.root, "mpy_pico_w_v1.0.0.manifest")
        write_manifest(manifest, manifest_path)
        loaded = validate_firmware_pair(zip_path, manifest_path)
        self.assertEqual(loaded["kind"], KIND_MICROPYTHON_APP)

    def test_scan_firmwares_dir(self):
        firmwares = os.path.join(self.root, "firmwares")
        os.makedirs(firmwares)
        zip_path, _, _ = self._valid_native_pair("scan_pico_v1.0.0")
        os.rename(zip_path, os.path.join(firmwares, "scan_pico_v1.0.0.zip"))
        os.rename(
            os.path.join(self.root, "scan_pico_v1.0.0.manifest"),
            os.path.join(firmwares, "scan_pico_v1.0.0.manifest"),
        )
        scanned = scan_firmwares_dir(firmwares)
        self.assertEqual(len(scanned), 1)
        self.assertEqual(scanned[0]["id"], "scan_pico_v1.0.0")

    def test_scan_orphan_zip(self):
        firmwares = os.path.join(self.root, "firmwares")
        os.makedirs(firmwares)
        self._write_zip(
            os.path.join(firmwares, "orphan_pico_v1.0.0.zip"),
            {"payload.uf2": b"x"},
        )
        with self.assertRaises(FirmwareManifestError) as ctx:
            scan_firmwares_dir(firmwares)
        self.assertIn("without sidecar", str(ctx.exception))

    def test_load_manifest_rejects_bad_target(self):
        zip_path, manifest_path, manifest = self._valid_native_pair()
        manifest["targets"] = ["esp32"]
        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle)
        with self.assertRaises(FirmwareManifestError):
            load_manifest(manifest_path)

    def test_scan_missing_dir(self):
        self.assertEqual(scan_firmwares_dir(os.path.join(self.root, "missing")), [])


if __name__ == "__main__":
    unittest.main()
