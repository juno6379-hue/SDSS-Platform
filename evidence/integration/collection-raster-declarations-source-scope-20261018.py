"""Reconstruct the approved collector-only byte edits from the pinned baseline."""
from pathlib import Path
import ast,hashlib,json,subprocess
from datetime import datetime
ROOT=Path(__file__).resolve().parents[2]
BASE='bd03292ea12f642839c96b753b752061725ef8d2'
NAME='scripts/collect_samples.py'
old=subprocess.check_output(['git','show',BASE+':'+NAME],cwd=ROOT)
new=(ROOT/NAME).read_bytes()
edits=[
('''                with rasterio.open(image_path, "w", **profile) as dst:
                    dst.write(np.stack(arrays))
                valid = np.all(np.stack(arrays) != 0, axis=0)
''','''                stack = np.stack(arrays)
                with rasterio.open(image_path, "w", **profile) as dst:
                    dst.write(stack)
                    for index, asset in enumerate(bands, 1):
                        dst.set_band_description(index, pc_band_keys.get(asset, asset))
                valid = np.all(np.isfinite(stack) & (stack != 0), axis=0)
'''),
('''                with rasterio.open(quality_path, "w", **{**profile, "count": 1, "dtype": "uint8", "nodata": 0}) as dst:
                    dst.write(valid.astype("uint8"), 1)
''','''                with rasterio.open(quality_path, "w", **{**profile, "count": 1, "dtype": "uint8", "nodata": None}) as dst:
                    dst.write(valid.astype("uint8"), 1)
                    dst.set_band_description(1, "binary_validity")
'''),
('''                           reflectance_conversion_verified=False, quality_mask_path=str(quality_path),
''','''                           reflectance_conversion_verified=False, quality_mask_path=str(quality_path),
                           quality_mask_semantics={"schema_version": 1, "kind": "binary_validity", "valid_value": 1, "invalid_value": 0},
''')]
reconstructed=old
for before,after in edits:
    assert reconstructed.count(before.encode())==1
    reconstructed=reconstructed.replace(before.encode(),after.encode(),1)
assert reconstructed==new
assert b'\r\n' not in old and b'\r\n' not in new
def other_nodes(raw):
    return [ast.dump(n,include_attributes=False) for n in ast.parse(raw.decode('utf-8')).body
        if not (isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name=='collect_windows')]
assert other_nodes(old)==other_nodes(new)
record={'recorded_at':datetime.now().astimezone().isoformat(),'scope':'APPROVED_COLLECT_WINDOWS_EDITS_ONLY',
    'baseline_commit':BASE,'path':NAME,'before_sha256':hashlib.sha256(old).hexdigest(),
    'after_sha256':hashlib.sha256(new).hexdigest(),'exact_reconstruction_from_three_declared_edits':True,
    'other_top_level_ast_unchanged':True,'raw_lf_preserved':True,
    'approved_edits':[{'before':before,'after':after} for before,after in edits],
    'baseline_or_operating_collection_executed':False,'data_files_written_by_this_audit':0}
(ROOT/'evidence/integration/collection-raster-declarations-source-scope-20261018.json').write_text(
    json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k!='approved_edits'}))
