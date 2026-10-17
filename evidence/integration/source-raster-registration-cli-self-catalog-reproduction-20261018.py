"""Reproduce only in an owned Temp fixture; never inspect the operating catalog."""
import hashlib
import json
from pathlib import Path
from test_source_raster_registration_cli import SourceRasterRegistrationCLITests
from scripts import register_dataset_version as cli

case = SourceRasterRegistrationCLITests()
case.setUp()
try:
    before = hashlib.sha256(case.store.db.read_bytes()).hexdigest()
    case.manifest.update(artifact_uri='catalog.sqlite3',sha256=before)
    case.save()
    code,result = cli.run(case.args())
    after = hashlib.sha256(case.store.db.read_bytes()).hexdigest()
    proof = {'scope':'TEMP_ONLY_OLD_CLI_SELF_CATALOG_ARTIFACT_REPRODUCTION',
        'source_sha256':hashlib.sha256(Path('scripts/register_dataset_version.py').read_bytes()).hexdigest(),
        'exit_code':code,'status':result['status'],'declared_artifact_sha256':before,
        'actual_artifact_sha256_after_registration':after,'success_ref_immediately_matches_actual_bytes':before == after,
        'registry_rows':len(case.store.list('dataset_versions')),'operating_access':0}
    Path('evidence/integration/source-raster-registration-cli-self-catalog-reproduction-20261018.json').write_text(
        json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(proof))
finally:
    case.doCleanups()
