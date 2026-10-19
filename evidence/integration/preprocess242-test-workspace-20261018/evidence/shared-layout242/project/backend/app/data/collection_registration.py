"""Register verified local collection reports in the common DatasetVersion registry.

Explicit source-document registration only; never grants a quality/training gate.
"""
import hashlib
import json
from pathlib import Path
import re

from ..dataset_registry import canonical_manifest, register_version, resolve_version
from ..sdss_results import local_asset
from .recovery_terminal import _confined, _pairs, _constant, _finite


PROVINCES = frozenset(("south_sulawesi", "gorontalo", "southeast_sulawesi", "banten", "west_java", "east_java"))
MAX_REPORT_BYTES = 64 * 1024 * 1024
MAX_REGISTRY_MANIFEST_BYTES = 1024 * 1024


def read_registration_json(path, maximum=MAX_REGISTRY_MANIFEST_BYTES):
    """Strict bounded JSON for the explicitly selected registration inputs."""
    path = Path(path)
    before = path.stat()
    if not path.is_file() or before.st_size > maximum:
        raise ValueError("Registration JSON exceeds its file limit.")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    after = path.stat()
    fingerprint = lambda item: (item.st_size, item.st_mtime_ns, item.st_ctime_ns)
    if len(raw) > maximum or fingerprint(before) != fingerprint(after):
        raise ValueError("Registration JSON changed or exceeds its file limit.")
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
        _finite(document)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError("Registration JSON is invalid.") from None
    if type(document) is not dict:
        raise ValueError("Registration JSON must be an object.")
    return document, hashlib.sha256(raw).hexdigest()


def _verified_file(root, value, expected):
    if type(value) is not str or type(expected) is not str or re.fullmatch("[a-f0-9]{64}", expected) is None:
        raise ValueError("Each source file needs an explicit local path and SHA-256.")
    path = _confined(root, value)
    before = path.stat()
    if not path.is_file():
        raise ValueError("Source artifact must be a file.")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    after = path.stat()
    marker = (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
    if marker != (after.st_size, after.st_mtime_ns, after.st_ctime_ns) or digest.hexdigest() != expected:
        raise ValueError("Source artifact changed or its SHA-256 differs.")
    return path, marker


def register_collection_version(store, report_path, registry_manifest, *, expected_dataset_id):
    """Verify all completed source rows, then write only dataset_versions.

    The source report remains a RAW/STAGED document, not an AI-ready raster.
    A caller must supply every GMAIS identity/source/spatial/temporal/lineage field.
    """
    root = Path(store.root).resolve()
    manifest, _ = canonical_manifest(registry_manifest)
    if manifest["dataset_id"] != expected_dataset_id:
        raise ValueError("CLI id must match the explicit Dataset Manifest identity.")
    if manifest["data_type"] != "document" or manifest["quality_status"] not in ("RAW", "STAGED"):
        raise ValueError("Collection registration accepts only RAW/STAGED source documents.")
    requested_report_path = report_path
    report_path = _confined(root, report_path)
    if local_asset(root, manifest["artifact_uri"]) != report_path:
        raise ValueError("Dataset artifact must be the selected collection report.")
    report, report_sha = read_registration_json(report_path, MAX_REPORT_BYTES)
    if manifest["sha256"] != report_sha:
        raise ValueError("Collection report SHA-256 differs from the Dataset Manifest.")
    scenes = report.get("scenes")
    if type(scenes) is not list or not 1 <= len(scenes) <= 20000 or any(type(row) is not dict for row in scenes):
        raise ValueError("Collection report scenes are invalid or exceed the row limit.")
    state = None
    source_files = {}
    logical_sources = []
    downloaded = 0
    for row in scenes:
        if row.get("status") != "rgb_window_downloaded":
            continue
        province, year = row.get("aoi"), row.get("year")
        if type(province) is not str or province not in PROVINCES:
            raise ValueError("Completed source row must identify a First Group province.")
        if not ((type(year) is int and 2020 <= year <= 2025)
                or (type(year) is str and year in tuple(str(y) for y in range(2020, 2026)))):
            raise ValueError("Completed source row must identify an explicit 2020..2025 year.")
        if "province" in row and row["province"] != province:
            raise ValueError("Source province identities conflict.")
        hashes = row.get("patch_sha256")
        if hashes is not None:
            if type(hashes) is not dict:
                raise ValueError("Source patch hashes must be an object.")
            evidence = {name: {"path": row.get(field), "sha256": hashes.get(name)}
                        for name, field in (("image", "image_path"), ("label", "label_path"), ("quality", "quality_mask_path"))}
        else:
            if state is None:
                state_path = _confined(root, report_path.parent / "window-state.json")
                state, _ = read_registration_json(state_path, MAX_REPORT_BYTES)
            cells = state.get("cells")
            evidence = cells.get(f"{province}-{year}") if type(cells) is dict else None
        if type(evidence) is not dict:
            raise ValueError("Completed source row has no file-integrity evidence.")
        for field in ("image", "label", "quality"):
            record = evidence.get(field)
            if type(record) is not dict:
                raise ValueError("Image, label and quality SHA evidence are all required.")
            path, marker = _verified_file(root, record.get("path"), record.get("sha256"))
            # Window-state evidence must refer to the row's actual artifact.
            row_field = {"image": "image_path", "label": "label_path", "quality": "quality_mask_path"}[field]
            if type(row.get(row_field)) is not str or _confined(root, row[row_field]) != path:
                raise ValueError("Source row and integrity evidence refer to different files.")
            source_files[path] = marker
            logical_sources.append((row[row_field], path))
        downloaded += 1
    if not downloaded:
        raise ValueError("No completed, hash-verified collection rows are available.")
    seen = set()
    for parent in manifest["lineage"]:
        identity = (parent["id"], parent["version"])
        if identity == (manifest["dataset_id"], manifest["version"]) or identity in seen:
            raise ValueError("Self or duplicate lineage references are not allowed.")
        seen.add(identity)
        resolve_version(store, parent["id"], parent["version"], parent["sha256"])
    # Recheck files before the single registry write; no immutable file snapshot is claimed.
    for requested, expected_path in logical_sources:
        if _confined(root, requested) != expected_path:
            raise ValueError("Source artifact path changed before registration.")
    for path, marker in source_files.items():
        current = path.stat()
        if marker != (current.st_size, current.st_mtime_ns, current.st_ctime_ns):
            raise ValueError("Source artifact changed before registration.")
    if (_confined(root, requested_report_path) != report_path
            or local_asset(root, manifest["artifact_uri"]) != report_path
            or read_registration_json(report_path, MAX_REPORT_BYTES)[1] != report_sha):
        raise ValueError("Collection report changed before registration.")
    record = register_version(store, manifest)
    return {"dataset_version": record, "downloaded_windows": downloaded,
            "verified_file_count": len(source_files), "training_ready": False,
            "scientific_accuracy_validated": False, "deployment_approval": False,
            "quality_gate": "SOURCE_FILE_HASHES_ONLY"}
