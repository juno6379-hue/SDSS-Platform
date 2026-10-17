"""Compare the patch producer with its published baseline; no producer execution."""
import ast
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = 'a3f4a94a69ad0f5c54a9af76bf6af82053e1a419'
NAME = 'scripts/collect_training_grid.py'
before = subprocess.run(['git', 'show', BASE+':'+NAME], cwd=ROOT, check=True, capture_output=True).stdout
after = (ROOT/NAME).read_bytes()
edits = [
    (b'                            dst.write(data)\n                    row = copy.deepcopy(source)\n',
     b'                            dst.write(data)\n                            if name == "image":\n                                for index, description in enumerate(image.descriptions, 1):\n                                    if description is not None:\n                                        dst.set_band_description(index, description)\n                    row = copy.deepcopy(source)\n'),
    (b'                    row = copy.deepcopy(source)\n',
     b'                    row = copy.deepcopy(source)\n                    row.pop("quality_mask_semantics", None)\n                    row["training_support_mask_semantics"] = {"schema_version": 1, "kind": "training_support", "valid_value": 1, "invalid_value": 0}\n')]
expected = before
for old_bytes, new_bytes in edits:
    assert expected.count(old_bytes) == 1
    expected = expected.replace(old_bytes, new_bytes, 1)
assert expected == after
old, new = ast.parse(before.decode('utf-8')), ast.parse(after.decode('utf-8'))
def others(tree):
    return [ast.dump(n, include_attributes=False) for n in tree.body
            if not (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == 'materialize_patches')]
assert others(old) == others(new)
assert b'\r' not in before and b'\r' not in after
assert before != after
result = {'recorded_at':datetime.now().astimezone().isoformat(), 'scope':'MATERIALIZE_PATCHES_ONLY',
          'baseline_commit':BASE, 'path':NAME, 'before_sha256':hashlib.sha256(before).hexdigest(),
          'after_sha256':hashlib.sha256(after).hexdigest(), 'other_top_level_ast_unchanged':True,
          'exact_reconstruction_from_two_declared_edits':True,
          'raw_lf_preserved':True, 'baseline_or_operating_producer_executed':False}
(ROOT/'evidence/integration/grid-patch-declarations-source-scope-20261018.json').write_text(
    json.dumps(result, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result))
