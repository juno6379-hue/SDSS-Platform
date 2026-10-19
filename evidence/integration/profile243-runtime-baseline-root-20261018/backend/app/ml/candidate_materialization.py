"""Evidence-only candidate materialization through existing bounded writer/validator."""
import copy
from pathlib import Path
import re
from .split_json_io import BoundedJSONIO,_local,_stamp
from .split_validation import validate_split_repair_plan
from .split_planning import write_plan
from ..data.readiness_connectivity_witness import FIXED_PROVINCE_SPLITS
from ..data.recovery_terminal import _confined

INPUT_ROLES=('source','readiness','saved_plan')
BASENAMES=('plan.json','candidate.json','receipt.json')
RECEIPT_CAP=65536
POLICY={'input_caps':{'source':64*1024**2,'readiness':16*1024**2,'saved_plan':4*1024**2,'candidate':64*1024**2},'output_caps':{'plan':4*1024**2,'candidate':64*1024**2},'max_depth':32}


def _need(value,message):
    if not value:raise ValueError(message)


def _dir_identity(path):
    value=path.stat();_need(path.is_dir(),'Existing output parent directory required')
    return (value.st_dev,value.st_ino,value.st_ctime_ns)


def materialize_split_candidate(data_root,paths,pins,output_dir,*,evidence_root):
    """Create a new metadata-only evidence package; receipt is written last.

    No pixels/assess/registry/training. A valid receipt is not training approval.
    Failures preserve new partial artifacts and raise; no automatic cleanup.
    """
    _need(type(paths) is dict and set(paths)==set(INPUT_ROLES) and type(pins) is dict and set(pins)==set(INPUT_ROLES),'Exactly three input paths and SHA pins required')
    _need(all(type(p) is str and re.fullmatch('[0-9a-f]{64}',p) is not None for p in pins.values()),'Explicit lowercase SHA pins required')
    roots=[_local(data_root),_local(evidence_root)];resolved=[p.resolve() for p in roots]
    for root in resolved:_local(root);_need(root.is_dir(),'Existing local input roots required')
    data,evidence=resolved;_need(not evidence.is_relative_to(data),'Evidence root must be outside DATA')
    logical={};targets={};stamps={}
    for role in INPUT_ROLES:
        scope=data if role!='saved_plan' else evidence
        value=Path(paths[role]);value=value if value.is_absolute() else scope/value
        logical[role]=_local(value);targets[role]=_confined(scope,logical[role]);_local(targets[role]);stamps[role]=_stamp(targets[role].stat())
        _need(stamps[role][0]<=POLICY['input_caps'][role],'Input exceeds role byte cap')
    _need(len(set(targets.values()))==3 and len({(s[3],s[4]) for s in stamps.values()})==3,'Inputs must be distinct regular files')
    out=_local(output_dir);target=_confined(evidence,out);_need(not target.is_relative_to(data),'Output must be outside DATA')
    _need(not out.is_symlink() and not out.exists(),'New explicit output directory required')
    parent=out.parent.resolve();parent_id=_dir_identity(parent)
    _need(target.parent==parent and all(target/name not in targets.values() for name in BASENAMES),'Output/input alias prohibited')
    io=BoundedJSONIO(copy.deepcopy(POLICY));docs={role:io.read(logical[role],role,pins[role])[0] for role in INPUT_ROLES}
    def check_paths():
        _need(all(p.resolve()==r for p,r in zip(roots,resolved)),'Input root target changed')
        for role in INPUT_ROLES:
            scope=data if role!='saved_plan' else evidence
            _need(_confined(scope,logical[role])==targets[role],'Input target changed')
        _need(out.resolve()==target and out.parent.resolve()==parent and _dir_identity(parent)==parent_id and not out.is_symlink(),'Evidence parent or output target changed')
        _need(not out.exists(),'New output directory already exists')
    plan=docs['saved_plan'];_need(type(plan) is dict,'Saved plan must be JSON object')
    verified=validate_split_repair_plan(logical['saved_plan'],logical['source'],pins['source'],province_splits=dict(FIXED_PROVINCE_SPLITS),readiness_path=logical['readiness'],readiness_sha256=pins['readiness'],data_root=data,io_policy=io)
    _need(verified.get('status')=='METADATA_INTEGRITY_VERIFIED' and verified.get('plan_integrity_valid') is True and verified.get('ready_for_training') is False and verified.get('training_executed') is False and verified.get('scientific_accuracy_validated') is False,'Plan full metadata validation failed')
    io.verify();check_paths();out.mkdir(exist_ok=False);created_id=_dir_identity(out)
    # Directory ctime changes when children are created on Windows, so identity checks
    # below use only dev/inode for the new directory (parent identity stays fixed).
    plan_out=target/BASENAMES[0];candidate_out=target/BASENAMES[1];receipt_out=target/BASENAMES[2]
    write_plan(plan,plan_out,derived_manifest=candidate_out,io_policy=io)
    plan_document,plan_sha=io.read(plan_out,'saved_plan');candidate,candidate_sha=io.read(candidate_out,'candidate')
    output_identities=[_stamp(p.stat())[3:] for p in (plan_out,candidate_out)]
    _need(len(set(output_identities))==2 and not set(output_identities)&{s[3:] for s in stamps.values()},'Generated files must be distinct from each other and inputs')
    _need(type(candidate) is dict and candidate.get('status')=='PLANNED_DERIVED_CANDIDATE' and candidate.get('executed') is False and candidate.get('learning_ready') is False,'Candidate false approval contract invalid')
    roundtrip=validate_split_repair_plan(plan_out,logical['source'],pins['source'],province_splits=dict(FIXED_PROVINCE_SPLITS),readiness_path=logical['readiness'],readiness_sha256=pins['readiness'],data_root=data,candidate_path=candidate_out,candidate_sha256=candidate_sha,io_policy=io)
    _need(roundtrip.get('status')=='METADATA_INTEGRITY_VERIFIED' and roundtrip.get('ready_for_training') is False and roundtrip.get('training_executed') is False and roundtrip.get('scientific_accuracy_validated') is False and roundtrip.get('plan_integrity_valid') is True and roundtrip.get('candidate_validation',{}).get('status')=='EXACT_METADATA_MATCH' and roundtrip['candidate_validation'].get('candidate_integrity_valid') is True,'Candidate exact metadata roundtrip failed')
    receipt={'schema_version':1,'kind':'EVIDENCE_SPLIT_CANDIDATE_RECEIPT','status':'METADATA_ROUNDTRIP_VERIFIED','candidate_status':'PLANNED_DERIVED_CANDIDATE','readiness_status':'BLOCKED','scope':'PINNED_JSON_METADATA_ONLY_NOT_RASTER_READINESS',
      'inputs':{role:{'path':str(targets[role]),'sha256':pins[role],'bytes':stamps[role][0]} for role in INPUT_ROLES},
      'outputs':{'plan':{'name':BASENAMES[0],'sha256':plan_sha,'bytes':plan_out.stat().st_size},'candidate':{'name':BASENAMES[1],'sha256':candidate_sha,'bytes':candidate_out.stat().st_size}},
      'derived_manifest_version':plan_document['derived_manifest_version'],'fixed_province_splits':dict(FIXED_PROVINCE_SPLITS),'source_row_count':len(docs['source']['scenes']),'candidate_row_count':len(candidate['scenes']),'excluded_source_row_count':len(plan['excluded_row_indexes']),'projected_after':copy.deepcopy(plan['projected_after']),
      'metadata_integrity_verified':True,'raster_readiness_rechecked':False,'source_rows_modified_or_reassigned':False,'executed':False,'learning_ready':False,'ready_for_training':False,'scientific_accuracy_validated':False,'source_authenticity_verified':False,'exact_row_binding_verified':False,'spatial_overlap_rechecked':False,'exact_class_counts_recomputed':False,'training_split_leakage_resolved':False,'execution_authorized':False,'registry_called':False,'settlement_authorized':False,'automatic_resume_allowed':False,'proposed_refund_bytes':0,'exactly_once_applied':'UNKNOWN',
      'completion_contract':'Receipt requires strict schema and output SHA verification; absent or invalid receipt means incomplete. Final stability check immediately precedes exclusive receipt write; no atomic multi-file snapshot guarantee.'}
    receipt_io=BoundedJSONIO({'input_caps':dict(POLICY['input_caps']),'output_caps':{'plan':RECEIPT_CAP,'candidate':RECEIPT_CAP},'max_depth':32});size=receipt_io.measure(receipt,'plan')
    # ctime of directories changes as files are added: compare inode/device here.
    _need(_dir_identity(out)[:2]==created_id[:2],'New output directory replaced')
    io.verify()
    _need(all(p.resolve()==r for p,r in zip(roots,resolved)) and out.resolve()==target and out.parent.resolve()==parent and _dir_identity(parent)[:2]==parent_id[:2] and _dir_identity(out)[:2]==created_id[:2] and not out.is_symlink(),'Final path identity changed')
    _need(not receipt_out.exists() and not receipt_out.is_symlink(),'Receipt must be new')
    # No post-receipt input check: an exception after a completed receipt must not
    # leave a success-looking marker for a failed final input verification.
    receipt_io.write(receipt_out,receipt,'plan',size)
    return receipt
