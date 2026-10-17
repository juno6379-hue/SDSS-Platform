# 77. 실행 입력 전달 선언의 ordered binding 대조

## 2026-10-17 — 선택 노드와 제안 Job의 입력 전달 계약(86)

신규 `backend/app/workflow_node_input_handoff.py:compare_workflow_node_input_handoff`는 caller-pinned 전체 Workflow request와 선택 node_id를 제안 Job의 제한된 metadata와 순수 대조한다. agent_id·capability_id·execution_context.trace_id 및 ordered input_refs의 id/version/sha256·role/URI의 부재와 값을 비교한다. pin에는 선택외 node·policy·dependency도 포함되지만 SHA 일치는 신뢰한 원본 인증이 아니다.

이 함수는 전체 Job 생성기/검증기가 아니다. 기존 Workflow 계획·DAG 검사·현재 Registry/파일 진단·79~85의 기존 Job 검증을 호출하거나 대신하지 않는다. 선택외 빈입력은 보존하고 선택node 빈입력만 차단한다. 전체 DAG cycle을 검사하지 않아 선언이 같으면 cycle 포함 요청도 MATCH일 수 있으며 dag_validated=false다. AOI·requested_outputs·선행 Result를 추정하지 않고 Job/Result·실제 executor/학습을 시작하지 않는다. 공개 API/UI 연결은 없고 기존 응답/화면을 유지한다. 세부 지원subset·한도·순수함수 사용법·시험/한계는 [문서86](86_workflow_node_input_handoff.md)에 기록한다.

## 2026-10-17 저장 expected·supplied 순수 handoff 대조 (81)

`compare_stored_job_binding_handoff(job,requested_job_id,supplied_envelope)`는 저장 Job/capture의79 형식·신원·hash 검증과77의 ordered binding 대조를 연결하는 내부 순수 함수다. 별도 caller expected 인자를 받지 않으며 RECORDED 저장 envelope만 expected로 사용한다. 잘못된 supplied/저장 Job·capture/신원·순서·role·pin 불일치는 BLOCKED가 우선한다. 유효 legacy/unavailable에서도 저장 request와 supplied의 눈에 보이는 연결을 검사하며, 그 연결은 같고 expected pin만 미기록이면 UNKNOWN이다. supplied나 현재 Registry로 과거 expected를 역채우지 않는다.

응답은 안전한 상태·계수·집계 배열 hash와 code/index만 제공한다. 12승인 및 current_files_revalidated/executor_bindings_compared/stored_job_origin_verified는 모두 false, 함수 자체의7IO계수는0이다. passed Job이 실제 저장소에서 왔는지 또는 supplied가 실제 실행자에서 수집됐는지 인증하지 않으며 caller가 양쪽 객체를 구성해 MATCH를 만들 수도 있다. 현재 파일·기관 ACL·TOCTOU/동시변조 원자성·학습준비/과학적 성능을 입증하지 않는다.

관련/독립 신규13 PASS(0.057초/0.056초), 실제 기존 legacy2의 선택 저장 선언을 로컬 supplied로 복사한8경우 UNKNOWN4/BLOCKED4·catalog14/Jobbody불변을 확인했다. 실제 executor 관측/생성된 production MATCH는 아니다. `evidence/integration/stored-binding-handoff-live-validation-20261017.json` 참조. 정확 결과 계약·safe enum·한계·시험은 [문서81](81_stored_job_binding_handoff.md)을 따른다. API/UI/executor/DB에는 미연결인 내부 단위이므로 기존79/80 공개 응답·카드·승인 gate는 그대로이며 직접 프론트/브라우저 재시험은 하지 않는다.

상태: **TESTED_SYNTHETIC / 내부 RFC v1 / 실행 미연결**. `backend/app/execution_input_binding.py`의 순수 함수 `compare_execution_input_bindings(expected, supplied)`는 제출 시 고정한 것으로 caller가 제공한 입력 선언과 실행기로 전달하려는 것으로 caller가 제공한 선언을 비교한다. 일치 결과도 실행·학습·과학·권한·파일 불변성 승인이 아니다. 기존 코어, upstream schema, API, UI, DB를 수정하지 않는다.

## 기존 기능과 새 경계

`dataset_registry.register_version`은 manifest와 자산을 확인하고 버전을 불변 등록한다. `resolve_job_inputs`는 현재 Registry와 자산/URI를 점검한다. `job_snapshot`은 제출 당시 저장 진단을 투영한다. 이번 helper는 이 기능을 호출하지 않으며 **두 ordered 메타데이터 envelope의 전달 일치**만 검사한다. 실제 executor나 제출 경로에 아직 연결하지 않았다.

upstream `contracts/upstream/GMAIS-v0.2/schemas/job-request.schema.json`의 input_ref는 id/version/sha256와 optional role/uri다. 신규 내부 envelope의 `manifest_sha256`는 별도 선택 확장이며 원래 Job schema를 변경하지 않는다. `sha256`는 자산 바이트의 선언 pin, `manifest_sha256`는 Registry의 canonical manifest digest에 해당하는 선언 pin이다. 이 helper는 실제 바이트·Registry 내용을 확인하지 않는다.

## 입력 계약

```text
expected, supplied: exact dict {
  job_id: bounded string,
  agent_id: bounded string,
  trace_id: bounded string,
  bindings: ordered list[1..64] of exact dict {
    input_index: exact int == list position,
    id: bounded string,
    version: bounded string,
    sha256: lowercase 64 hex,
    role?: bounded string,
    manifest_sha256?: lowercase 64 hex
  }
}
```

문자열은 exact str, 1..256자이며 공백만 있는 값·C0/C1 control·DEL·unpaired surrogate를 거부한다. 길이를 스캔/UTF8 인코딩보다 먼저 검사한다. 대소문자 변경, 공백 제거, 역할 기본값 채우기, 문자열 강제 변환은 하지 않는다. version의 trim/lower 값이 latest/current면 고정 버전이 아니므로 거부한다. index는 bool/float를 허용하지 않는다. dict/list는 exact built-in 타입만 지원하며 unknown key, nested/cyclic 값은 flat typed schema에서 재귀/원문 직렬화 없이 거부한다. envelope/row key 수와 list 길이를 복사·hash보다 먼저 확인한다.

같은 id의 서로 다른 고정 version은 정상 복수 입력이다. 같은 id/version의 여러 entry도 선언 pin이 같으면 허용한다. 하지만 같은 id/version의 자산 SHA가 다르거나 **명시된** manifest SHA끼리 상충하면 각 envelope 내부에서 차단한다. role은 한 Dataset을 여러 용도로 쓰는 것을 허용하므로 identity conflict 기준에 포함하지 않으며 position별로 엄격 대조한다.

URI는 이 최소 계약에서 받지 않는다. 기존 resolver의 현재 URI 검사는 별도 경계다. AOI, model, parameter, 권한, 실제 파일/자산·manifest의 진실성은 이번 비교 범위 밖이다.

## 상태 우선순위와 legacy

1. schema/type/상한·내부 pin 충돌·Job/Agent/Trace·binding 개수·순서·id/version/SHA/role의 presence 또는 값 불일치는 **BLOCKED**다.
2. 다른 차단이 없어도 expected의 manifest pin이 하나라도 미기록이면 **UNKNOWN**이다. supplied에 새 manifest pin이 있어도 expected를 소급 채우지 않는다.
3. 모든 expected manifest pin이 명시되어 있고 모두 대조에 일치하면 **MATCH**다.

expected manifest pin이 명시된 경우 supplied의 누락/불일치는 BLOCKED다. role이 양쪽 모두 부재이면 동일한 '미기록'으로 비교하지만 null/빈 문자열/default role로 추정하지 않는다. role이 한쪽에만 있으면 BLOCKED다. expected manifest pin 미기록과 role 부재의 의미는 다르다. 동일 id/version의 다른 row에 manifest pin이 있어도 현재 row의 미기록 pin으로 전파하지 않고 UNKNOWN을 유지한다.

## 결과와 hash

최상위 schema_version1, scope `ORDERED_BINDING_DECLARATIONS_ONLY`, status MATCH/BLOCKED/UNKNOWN, issues, expected_bindings_sha256, expected_binding_count, supplied_binding_count, missing_expected_manifest_pin_count, declarations_match를 반환한다. issues는 exact `{side,input_index,code}`이며 side는 expected/supplied/comparison, index는 null 또는0..63이다. 원래 id/version/SHA/role/URI/입력 원문·예외는 결과에 담지 않는다.

expected_bindings_sha256는 schema-valid expected **bindings 배열만**의 SHA256다. Python `json.dumps(sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':'))`의 UTF8 바이트를 사용하며 RFC8785 보장이 아니다. 순서·optional key 존재·role·manifest pin이 모두 포함된다. Job/Agent/Trace를 포함한 전체 실행 요청 digest가 아니며 이 신원은 별도로 대조한다. invalid expected에는 digest=null이다. supplied가 invalid여도 valid expected의 digest는 반환할 수 있다. UNKNOWN의 미기록 계수는 양쪽 schema가 valid할 때만 계산한다.

`declarations_match`는 MATCH에서만 true이며 인증 flag가 아니다. execution_authorized/ready_for_execution/ready_for_training/scientific_approval/acl_verified/registry_verified/training_authorized/pixels_verified/toc_tou_protected/executor_connected/artifact_bytes_verified/manifest_bytes_verified는 모두 false다. network_requests/source_files_written/database_calls/resolver_calls/executor_calls는0이다. hash 입력 자체의 진실성, expected의 신뢰성, 파일 TOCTOU 방지는 증명하지 않는다.

## 합성 검증과 통합 한계

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend;$PWD\tests"
python -m unittest test_execution_input_binding -v
```

최종 관련 시험은 **14 PASS /0.037초 /종료0**이다. 관련 합성14개 시험은 MATCH·다른 버전·동일 pin 반복, ordered 교환/인덱스/누락/추가, Job/Agent/Trace 변조, role presence와 hash, legacy UNKNOWN 및 supplied pin 역채움 금지, expected pin 누락/변조 차단, 양쪽 내부 SHA 충돌, bool/float/hugeint/대문자 SHA/latest/current, 문자열 상한/control/surrogate, unknown keys/cycle/64상한, canonical hash 범위, 입력 불변/무IO, 안전 결과를 검사한다. 로그는 `evidence/integration/execution-input-binding-related-20261017.log`다. 초기 privacy 시험은 짧은 id `rain`이 결과 키 `training`의 부분 문자열에도 나타나는 잘못된 assertion 때문에 실패했고, 인용된 JSON scalar로 검사하도록 시험을 고쳤다. 생산 데이터 누출 재현은 아니다.

현재 저장 Job에는 manifest pin/실제 executor 전달 capture가 없을 수 있다. Root의 선택 메타데이터 replay는 expected/supplied를 같은 저장 요청에서 로컬 구성한 비교이며 **실제 executor capture가 아니다**. 이런 legacy는 UNKNOWN을 유지한다. 신뢰하는 제출 snapshot에서 expected를 구성하고 실제 executor 전달값을 포착하는 후속 adapter가 필요하다. 이번 함수는 Registry 읽기/등록, 파일/네트워크/DB IO, executor 실행, readiness/학습 gate 변경을 수행하지 않는다. 공개 API/UI/CLI를 추가하지 않는 순수 내부 단위이므로 이번 직접 화면 변경·브라우저 검증은 없다. Root가 실제 저장 메타데이터의 선택 검증·전체 회귀·보존·인계·이해자료를 별도 수행한다.

독립 최종 시험도 **14 PASS /0.014초 /종료0**이며 `evidence/integration/execution-input-binding-independent-20261017.log`에 기록했다. 별도 valid-envelope oracle648조합은 MATCH6/UNKNOWN9/BLOCKED633으로 모두 기대 결과와 일치했다. 이는 별도 실험으로 unittest14개나 Root 전체 회귀 건수에 합산하지 않는다. 독립 검토에서 추가 결함은 발견하지 않았다.


## 실제 저장 legacy 선언의 로컬 replay

Root는 SQLite를 read-only로 열어 기존 gmais_jobs2건의 저장 request·Job/Agent/Trace 신원을 확인했다. 두 기록 모두 제출 input_resolution과 manifest pin이 미기록이다. 원래 request의 id/version/asset SHA/optional role만 선택하고 배열 위치로 input_index를 구성했다. URI/AOI/model/params는 이 최소 계약에 포함하지 않는다. expected도 신뢰 제출 capture가 아닌 저장 request의 선택 선언이며 supplied는 실제 executor capture가 아니라 로컬 복사/변조 replay다.

각 Job에서 같은 선택 선언과 임의 manifest pin 추가는 UNKNOWN, version/Trace 변경은 BLOCKED였다. 합계8개 관측(UNKNOWN4/BLOCKED4)은 단위시험14개·독립648조합·전체 회귀 건수에 합산하지 않는다. 임의 추가 pin은 현재 Registry에서 조회한 값이 아니며 과거 미기록을 보강하지 않는다. expected bindings SHA를 독립 canonical 산식과 대조하고 caller 원본 불변·raw identity 비노출·모든 승인false/순수 함수 IO0을 확인했다. Root의 SQLite 읽기 자체는 helper의 무IO 범위와 구별한다.

`evidence/integration/execution-input-binding-live-replay-20261017.py`와 `execution-input-binding-live-validation-20261017.json`이 근거다. 기존 Job body hash와 catalog14행 전체 body의 전후 동일성·canonical SHA를 확인했다. 실제 executor/Job 실행·artifact/manifest 바이트 인증·학습은0이며 실제 MATCH 관측을 주장하지 않는다. 최종 전체 backend 회귀는789개 중788 PASS·기존 Windows symlink 제약1 SKIP /346.172초/종료0이다. `execution-input-binding-full-tests-20261017.log`가 근거이며 관련/독립14개·별도648조합·로컬replay8건은 중복 합산하지 않는다.


## 최종 보존·이해자료와 다음 통합

전체 시험 종료 뒤 보호141참조/기존코어35 SHA와catalog14행 canonical SHA를 재확인했다. 직전추적 backend/scripts/tests/data/frontend 변경0·기존Job body불변이다. 새구현/증거/문서를추가했으므로전체workspace/OS원자snapshot불변이라는뜻은아니다. `evidence/integration/execution-input-binding-live-integrity-20261017.json`과 이해자료 Gate·INDEX·대본/FAQ/변경이력 및 `execution-input-binding-closeout-20261017.json`을 따른다. 이번 공개API/UI변경·브라우저/프론트재시험은없다.

다음78 PLANNED는 새Job제출의같은resolver pass에서검증된record의manifestSHA를별도버전형capture로동일Job저장에함께기록하는통합이다. 기존input_resolution/HTTP응답·승인gate를보존하고과거Job/동일멱등replay를재조회/보강하지않는다. 현재78코드·실제DBJob쓰기·executor통합은없다. 신뢰expected구성과현재자산고정/TOCTOU·ACL/모델gate는실제실행전별도검증이필요하다.


## 제출 expected 구성의 후속 연결

[문서78](78_submission_binding_capture.md)은같은입력해석pass에서manifestpin을선택하여새Job별도extension에expectedenvelope를기록하는연결을구현했다. 이때77selfcompare로완전한선언shape를확인하지만실제executor전달supplied를비교하는소비경계는아직미통합이다. 기존legacy미기록을현재Registry로소급채우지않으며원문응답/gate도보존한다. 과거77의로컬replay관측과78의새captureTempStore시험·실제legacyGET호환확인은서로다른증거범위다.
