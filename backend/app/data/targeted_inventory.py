"""Fail-closed local support inventory for a targeted window; no dispatch."""
import hashlib
import json
import math
from pathlib import Path

from .targeted_bare_plan import _pinned, _json, _need, _polygon
from ..ml.per_scene_normalization_files import _root, _relative, _snapshot, _Blocked, _links

SOURCE = 'data/first-group-training-esri-v1/sources'
LABELS = {'raw-esri_io.tif', 'raw-worldcover.tif', 'label.tif', 'labels.tif', 'label-esri_io.tif'}


def _files(root, folder, maximum):
    """Enumerate without following links, including partial unreported batches."""
    result, pending = [], [(folder, 0)]
    while pending:
        directory, depth = pending.pop()
        _need(depth <= 12 and not _links(directory) and directory.resolve() == directory,
              'INVENTORY_PATH_INVALID')
        for path in directory.iterdir():
            _need(not _links(path) and path.resolve() == path, 'INVENTORY_PATH_INVALID')
            if path.is_dir():
                pending.append((path, depth + 1))
            elif path.suffix.lower() in ('.tif', '.tiff'):
                result.append(path)
                _need(len(result) <= maximum, 'INVENTORY_LIMIT')
    return sorted(result)


def inspect_targeted_inventory(project_root, request, *, max_files=10000, max_bytes=2*1024**3):
    """Verify observed source/support files and pending B02 footprints read-only.

    Scope is the fixed collection sources directory plus manifest source windows.
    Reference labels are enumerated but not treated as previously used imagery;
    their larger coverage is intentionally reusable for new label-mined windows.
    Every pending reservation needs matching config and an actual local raw B02.
    A projection comparison uses a conservative densified envelope plus one metre
    in projected CRS (1e-5 degrees for EPSG4326); it is not an independence proof.
    """
    out = {'schema_version': 1, 'scope': 'PINNED_LOCAL_COLLECTION_SUPPORT_INVENTORY',
           'status': 'BLOCKED', 'issue': None, 'execution_supported': False,
           'inventory_verified': False, 'pending_footprints_verified': False,
           'support_files_verified': 0, 'label_files_excluded': [], 'pending': [],
           'overlaps': [], 'assets': [], 'source_pins_verified': False,
           'scientific_independence_proven': False, 'training_ready': False}
    try:
        _need(type(request) is dict and request.keys() == {'manifest_ref', 'ledger_ref', 'target'}, 'REQUEST_INVALID')
        _need(type(max_files) is int and 1 <= max_files <= 10000 and
              type(max_bytes) is int and 1 <= max_bytes <= 4*1024**3, 'INVENTORY_LIMIT')
        root = _root(project_root)
        manifest_path, raw = _pinned(root, request['manifest_ref'], 128*1024**2)
        manifest = _json(raw)
        ledger_path, raw = _pinned(root, request['ledger_ref'], 8*1024**2)
        ledger = _json(raw)
        _need(type(manifest.get('scenes')) is list and type(ledger.get('batches')) is dict, 'INVENTORY_INVALID')
        target = request['target']
        _need(type(target) is dict and target.keys() == {'crs', 'corners'} and
              type(target['corners']) is list and len(target['corners']) == 4 and
              all(type(p) is list and len(p) == 2 and all(type(v) in (int,float) and math.isfinite(v) for v in p)
                  for p in target['corners']), 'TARGET_INVALID')
        from shapely.geometry import Polygon, box
        from rasterio.crs import CRS
        from rasterio.io import MemoryFile
        from rasterio.warp import transform_bounds
        import rasterio
        target_crs = CRS.from_user_input(target['crs'])
        target_polygon = Polygon(target['corners'])
        _need(target_crs.is_projected and target_polygon.is_valid and target_polygon.area > 0 and
              target_polygon.equals(box(*target_polygon.bounds)), 'TARGET_INVALID')
        folder = _relative(root, SOURCE, 'source')
        _need(folder.is_dir(), 'INVENTORY_UNAVAILABLE')
        # Older v1/smoke batches may be absent from the current aggregate but
        # their recorded source directories still participate across all years.
        roots = {folder}
        for row in ledger['batches'].values():
            if row.get('report_path') is not None:
                report = Path(row['report_path']) if Path(row['report_path']).is_absolute() else _relative(root, row['report_path'], 'report')
                _need(report.is_relative_to(root/'data') and report.parent.is_dir(), 'SOURCE_REPORT_UNAVAILABLE')
                roots.add(report.parent)
        roots = {p for p in roots if not any(p != other and p.is_relative_to(other) for other in roots)}
        def inventory():
            files = sorted({p for base in roots for p in _files(root, base, max_files)})
            _need(len(files) <= max_files, 'INVENTORY_LIMIT')
            return files
        before = inventory()
        assets = {p: None for p in before if p.name not in LABELS}
        out['label_files_excluded'] = [p.relative_to(root).as_posix() for p in before if p.name in LABELS]
        # Source windows from every row, regardless of year/quality, cannot be omitted.
        history = manifest.get('historical_noneligible_patches', [])
        _need(type(history) is list, 'INVENTORY_INVALID')
        for row in manifest['scenes'] + history:
            _need(type(row) is dict and type(row.get('source_window')) is dict, 'SOURCE_REFERENCE_MISSING')
            ref = row['source_window']
            path = Path(ref['path']) if Path(ref['path']).is_absolute() else _relative(root, ref['path'], 'source')
            _need(path.is_relative_to(root/'data') and type(ref.get('sha256')) is str, 'SOURCE_REFERENCE_INVALID')
            if path in assets and assets[path] is not None:
                _need(assets[path] == ref['sha256'], 'SOURCE_PIN_CONFLICT')
            assets[path] = ref['sha256']
        _need(len(assets) <= max_files, 'INVENTORY_LIMIT')
        configs = []
        for key, row in ledger['batches'].items():
            if row.get('status') != 'pending':
                continue
            directory = _relative(root, SOURCE+'/'+key, 'pending')
            config_path = directory/'config.json'
            digest, content = _snapshot(root, config_path, 2*1024**2, 'config', True)
            config = _json(content)
            _need(hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest() == row['config_sha256'],
                  'PENDING_CONFIG_MISMATCH')
            b02 = [p for p in before if p.is_relative_to(directory) and p.name == 'raw-B02.tif']
            _need(bool(b02), 'PENDING_IMAGE_FOOTPRINT_MISSING')
            configs.append((config_path, digest))
            out['pending'].append({'key': key, 'reserved_bytes': row['reserved_bytes'],
                                   'charged_bytes': row['charged_bytes'], 'b02_files': len(b02)})
        _need(sum(p.stat().st_size for p in assets) <= max_bytes, 'INVENTORY_LIMIT')
        signatures = {}
        with rasterio.Env(GDAL_PAM_ENABLED='NO', GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',
                          GDAL_GEOREF_SOURCES='INTERNAL', PROJ_NETWORK='OFF'):
            for path, expected in sorted(assets.items()):
                out['current_asset'] = path.relative_to(root).as_posix()
                st = path.stat()
                signatures[path] = (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
                digest, raw = _snapshot(root, path, 64*1024**2, 'support', True)
                _need(expected is None or digest == expected, 'SOURCE_PIN_MISMATCH')
                _need(raw[:4] in (b'II*\x00',b'MM\x00*',b'II+\x00',b'MM\x00+'), 'SUPPORT_RASTER_INVALID')
                with MemoryFile(raw) as memory, memory.open(driver='GTiff') as ds:
                    from shapely.geometry import box
                    t=ds.transform
                    _need(ds.crs is not None and (ds.crs.is_projected or ds.crs.to_epsg()==4326) and
                          t.b==t.d==0 and t.a>0 and t.e<0 and
                          all(math.isfinite(v) for v in ds.bounds), 'SUPPORT_RASTER_GRID_INVALID')
                    polygon = box(*ds.bounds)
                    _need(not ds.subdatasets and not ds.gcps[0] and ds.rpcs is None,
                          'SUPPORT_RASTER_INVALID')
                    if ds.crs == target_crs:
                        projected = target_polygon
                    else:
                        bounds = transform_bounds(target_crs, ds.crs, *target_polygon.bounds, densify_pts=1024)
                        _need(all(math.isfinite(v) for v in bounds), 'PROJECTION_INVALID')
                        pad = 1e-5 if ds.crs.is_geographic else 1.0
                        projected = box(bounds[0]-pad, bounds[1]-pad, bounds[2]+pad, bounds[3]+pad)
                    overlap = projected.intersection(polygon).area > 0
                    name = path.relative_to(root).as_posix()
                    out['assets'].append({'path': name, 'sha256': digest, 'crs': ds.crs.to_string(),
                                          'bounds': list(ds.bounds), 'overlap': overlap})
                    if overlap: out['overlaps'].append(name)
        _need(inventory() == before, 'INVENTORY_CHANGED')
        for path, stamp in signatures.items():
            st = path.stat()
            _need(not _links(path) and (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns) == stamp,
                  'INVENTORY_CHANGED')
        for path, pin in configs:
            _need(_snapshot(root, path, 2*1024**2, 'config')[0] == pin, 'INVENTORY_CHANGED')
        _need(_snapshot(root, manifest_path, 128*1024**2, 'manifest')[0] == request['manifest_ref']['sha256'] and
              _snapshot(root, ledger_path, 8*1024**2, 'ledger')[0] == request['ledger_ref']['sha256'], 'INVENTORY_CHANGED')
        out.update(inventory_verified=True, pending_footprints_verified=True,
                   source_pins_verified=True, support_files_verified=len(assets))
        _need(not out['overlaps'], 'EXISTING_SUPPORT_OVERLAP')
        out.update(status='LOCAL_INVENTORY_VERIFIED_EXECUTION_BLOCKED', issue='EXECUTION_GUARDS_NOT_CONNECTED')
    except _Blocked as exc:
        out['issue'] = exc.code
    except (ValueError, KeyError, TypeError, OSError) as exc:
        code = str(exc)
        out['issue'] = code if code.isupper() and code.replace('_','').isalpha() else 'LOCAL_INPUT_UNAVAILABLE'
    except Exception:
        out['issue'] = 'LOCAL_INPUT_UNAVAILABLE'
    return out
