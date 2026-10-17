# 86 — Workflow 선택 노드에서 제안 Job 입력 metadata로의 순수 전달 동등성

## 2026-10-17 — 완성 Job 초안 schema·metadata 내부 연결(89)

신규 `workflow_job_request_handoff.compare_workflow_job_request_handoff`는 사용자 완성 Job 초안의 bounded JSON/finite·원schema·날짜형식·bbox 숫자/순서를 확인하고, agent/capability/{trace}/ordered input_refs만 추출하여86에1회 대조한다. optional workflow_run_id가 있으면 caller Workflow와 같아야 하며 필드를 생성하거나 채우지 않는다. sourceasset/DB/Registry/실제Job/executor를 호출하지 않는다. 다만 원schema cold load는 local schema 읽기가 있어 단위전체 I/O0로 표현하지 않고 schema_files_read는 미계측 null이다.

fullJob 전체 canonical SHA는 이번 caller 초안의 관측값이며 별도 fullJobpin 인자가 없어 출처/과거초안 일치를 인증하지 않는다. metadata SHA는 부분범위로 AOI/output/purpose 변경 시 metadata MATCH와 전체초안 SHA가 다를 수 있다. AOI 소수좌표를 허용하고87/88 integer-only parser/canonical은 재사용하지 않는다. 기존환경의 date-time checker 미등록 공백은89 전용 detached checker/evolve로 보완했으며 기존 cachedvalidator/class·원schema/API는 변경하지 않았다. 원schema 및 지원검사 통과도 실제 Agent/model/과학적 AOI/output·ACL·DAG·학습/실행 승인이 아니다.

이번89는 공개API/UI 비연결의 내부 기능이다. 기존87/88 응답과 화면은 fullJob 검증을 제공한다고 표시하지 않고 그대로 유지한다. 사용법·새지원subset·오류/자원경계·합성시험·다음화면연결한계는 [문서89](89_workflow_job_request_handoff.md)를 참조한다.

## 2026-10-17 — Workflow 입력 전달 수동 API·UI 연결 (87/88)

순수86을 독립 내부 RFC `POST /v1/workflows/node-input-handoff`와 GeoQuery 실행계획 검토의 ‘Workflow 노드 입력 전달 선언 검사’에 연결했다. API는 원 Workflow/제안metadata JSON 문자열2개·caller canonical pin·명시 node_id의 정확4키를 받는다. 엄격UTF8·중복키/nonfinite/float·int32·원문별512KiB/전체1MiB·깊이/atom 한도 검사 후86을1회 호출한다. wrapper 전체 수신 rawbody SHA와 내부 canonical pin은 범위가 다르다. 고정400/413/503·no-store/기존인증을 유지하고 raw본문/URI/ID/예외를 응답하지 않는다.

UI는 원 planJson을 보존하며 node/제안metadata를 직접 입력하고 버튼을 눌러야만 검사한다. 기존 계획·현재 계보와 별도 상태이며 편집/node/proposal/revision/route/back/unmount가 이전 응답을 폐기한다. 전체요청 SHA·canonical pin·안전형식/indices/count/20false7IO0를 검증하고, Python/JS Unicode canonical fixture로 프로토콜을 대조했다. 기존 반환 plan.nodes 요약에서 원문을 재구성하지 않는다.

실제 로컬 HTTP와 브라우저에서 합성 caller선언의 MATCH/변조BLOCKED·미확인계수·원문검사·기존조회독립/뒤로가기를 확인했다. 이는 운영 Workflow/Job 전달의 검증이 아니다. MATCH는 완성Job/AOI/output/선행Result/DAG/원본인증/기관ACL/과학/학습/실제executor 승인을 부여하지 않는다. 신규 비교의 I/O0와 기존 plan/lineage의 Registry진단은 별도 범위다. 사용법·계약·시험/한계는 [API87](87_workflow_node_handoff_api.md)·[UI88](88_workflow_node_handoff_ui.md)를 따른다. 실제 Job 생성·실행·capture역채움은 없다.

상태: **TESTED_SYNTHETIC**. 내부 순수 함수 구현 및 격리 합성시험 완료. 공개 API·UI·실제 Workflow executor·Job POST에 연결하지 않았다. 전체 프로젝트 완료 또는 운영 승인 근거가 아니다.

## 문제와 구현

기존 Workflow 계획과 노드별 진단은 PLAN_ONLY이며, 선택 노드에서 제안하는 Job의 입력 선언이 그대로 전달되었는지는 별도 경계였다. 새 `backend/app/workflow_node_input_handoff.py`의 `compare_workflow_node_input_handoff(workflow_request, pinned_workflow_request_sha256, selected_node_id, proposed_job_metadata)`는 caller가 고정한 전체 원요청 SHA를 확인하고 선택된 노드의 선언과 제안 metadata를 비교한다. 기존 77~85 진단, Registry 조회, 파일 해시, Job 생성은 재실행하지 않는다.

이는 완성 Job의 유효성 검사가 아니다. 인자 `proposed_job_metadata`는 정확히 다음 네 필드만 가진다.

```json
{
  "agent_id": "selected-agent",
  "capability_id": "selected-capability",
  "execution_context": {"trace_id": "workflow-trace"},
  "input_refs": [{"id":"dataset","version":"v1","sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}]
}
```

원 Workflow schema에는 AOI·requested_outputs가 없다. 이 함수는 이를 생성하거나 기본값으로 채우지 않는다. predecessor Result를 input ref로 바꾸지 않으며, purpose/environment/approval_ref나 model/parameters를 추정하지 않는다. 위 metadata에 완성 Job 필드나 실행 context의 추가 필드를 넣으면 차단한다.

## 원 schema와 지원 subset

근거는 `contracts/upstream/GMAIS-v0.2/schemas/workflow-plan.schema.json` 및 `job-request.schema.json`이다. 원파일은 수정하지 않았다. 이 helper는 자원 예산과 불명확한 metadata 차단을 위해 아래의 더 좁은 subset을 지원한다.

- 정확한 내장 dict/list/str/int/bool 타입만 허용하며 형변환·정규화·trim은 하지 않는다. 문자열은 256 code point 이내이고 공백만인 문자열·C0/C1·surrogate를 거부한다. URI는 원 schema에 따라 명시적 빈 문자열도 허용하며, 부재와 빈 문자열은 다르다.
- Workflow 최상위는 schema_version(정확 `0.2.0`), workflow_run_id, trace_id, nodes, policy의 정확 5키다. node는 원 schema의 필수 5키 및 timeout_seconds/max_retries만 허용한다.
- 전체 node 수 1~128, 모든 node의 input_bindings 합계 최대 64다. 선택 외 node의 빈 입력은 보존하고 전체 SHA에 포함한다. 선택 node 또는 제안 metadata의 입력은 1~64개여야 한다.
- 입력 ref는 필수 id/version/sha256 및 선택 role/uri만 허용한다. SHA는 소문자 16진수 64자리이며 latest/current 버전은 거부한다. 같은 id의 다른 version은 가능하지만, 전체 Workflow 안의 같은 (id,version)이 다른 SHA를 선언하면 차단한다. 제안 refs 안에서도 같은 규칙을 적용한다.
- policy는 on_blocked(STOP_DEPENDENTS/FAIL_ALL), max_parallel, 선택 require_human_approval의 알려진 3키만 지원한다. 원 schema는 policy 확장 키를 허용하지만 이 함수는 모르는 키를 거부한다. max_parallel/timeout_seconds는 bool을 제외한 1~2147483647 정수, max_retries는 0~5 정수다. 원 schema보다 좁은 수치 상한이다.
- depends_on은 최대 128개의 bounded 문자열이다. 중복 간선은 원문 배열 그대로 SHA에 보존한다. node_id 중복은 선택 모호성으로 차단하고 미등록 dependency 및 자기 참조도 차단한다.
- **전체 DAG 순환·실행 순서·선행 Result 준비 여부는 검사하지 않는다.** 다중 node 순환이 있더라도 전달 선언이 같으면 MATCH일 수 있고 `dag_validated=false`다. 실제 DAG 판정은 기존 Workflow 기능과 별도의 실행 gate 책임이다.

정해진 키와 각 scalar/container 타입 및 크기를 먼저 확인하므로 임의의 중첩 JSON이나 재귀 container를 순회·직렬화하지 않는다. 알려진 구조에 끼워진 cycle도 타입/키 검사로 차단한다. 이는 상주 Python 객체에 대한 순수 검사의 예산이며 HTTP body byte/time/RAM 강제 한도가 아니다.

## SHA와 비교 계약

전체 Workflow 요청을 `json.dumps(sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')`로 직렬화한 SHA-256을 caller pin과 비교한다. dependency·policy·선택하지 않은 node·optional 키의 존재까지 포함하며, dict 삽입 순서는 의미가 없다. 배열 순서는 보존한다. 이 SHA는 caller가 제공한 요청의 동일성이고 원본 인증·전자서명·운영 Workflow 저장 증거가 아니다.

pin 일치 및 유일한 선택 이후 node agent_id/capability_id, Workflow trace_id, ordered input_bindings를 비교 대상 metadata로 삼는다. 제안 metadata의 agent_id/capability_id/execution_context.trace_id, ordered input_refs의 id/version/sha256, role/uri의 키 존재와 값을 엄격 비교한다. 입력의 재정렬도 차단한다. expected/proposed metadata SHA는 각각 검증된 구조에 대해서만 계산한다.

응답은 schema_version=1, scope=`WORKFLOW_NODE_TO_PROPOSED_JOB_INPUT_DECLARATIONS_ONLY`, status MATCH/BLOCKED, declarations_match, SHA 필드, 선택 node index, 검증된 입력 개수 또는 null, safe issues만 가진다. issue는 고정 code/side와 node_index/input_index이며 raw ID·URI·본문·예외문을 반환하지 않는다. 각 입력 필드 차이와 count/identity 차이는 구분하고, 구조 오류는 첫 안전 issue로 종료한다. null은 해당 검사가 관측되지 않았음을 의미한다.

`MATCH`는 caller 선언 전달의 동등성만 의미한다. 20개 false 항목에는 실행/학습 준비·권한·과학 승인·ACL·Registry·pixels·artifact/manifest bytes·TOCTOU·executor 연결·원본 인증·실 executor binding·전이 계보·완성 Job·AOI·output·predecessor binding·DAG가 포함된다. network/source read-write/DB/Registry/resolver/executor의 7개 계수는 모두 정수 0이다.

## 시험과 재현

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend;$PWD\tests"
python -m unittest test_workflow_node_input_handoff -v
```

`tests/test_workflow_node_input_handoff.py`: **13 PASS / 0.058초**. 로그: `evidence/integration/workflow-node-handoff-related-20261017.log`.

합성 자료로 MATCH 및 원문 불변·파일 open 금지·privacy/false/IO0, 전체 pin의 policy/선택외 node/dependency/optional 수정 감지, agent/capability/trace/각 ref 필드 mismatch, role/URI 존재와 빈 URI, 버전 구분/재정렬/상충 SHA, 빈/없는/모호 node, 비선택 빈 node 및 미검사 DAG 순환의 비승인 범위, 전체 64 ref/128 node 예산, unknown 및 완성 Job metadata 거부, int/bool/float/문자/버전 경계, 재귀 container, dependency shape/중복 원형보존을 확인했다. URI의 임의 객체 __eq__가 호출되기 전에 exactstr로 거부하고, 거대 policy enum 문자열도 길이 선검사하는 회귀를 추가했다. 운영 자료의 실행 전달, 파일 검증 또는 모델 성능 시험이 아니다. 독립/전체 회귀·보존 근거는 Root 인계 완료 후 추가한다.

## UI·인계·후속

이 단위는 신규 순수 내부 함수뿐이며 공개 route, workflow validation 응답, 기존 화면 계약을 바꾸지 않는다. 따라서 직접 UI 변경·프론트 재시험·실제 브라우저 검증은 이번 범위에 없고, Root가 web_ui에 함수/상태/오류·시험 근거를 인계하여 영향 검토를 기록한다. 후속 공개 API나 화면 연결은 별도 단위에서 source pin의 출처·입력 획득·stale state와 기존 gate를 함께 설계해야 한다. 이해 에이전트는 완료 코드와 합성 근거를 받아 쉬운 설명·발표 대본·FAQ·INDEX·변경 이력을 갱신한다.


## Root 실제 환경 관측과 직접 UI 영향

`evidence/integration/workflow-node-handoff-catalog-observation-20261017.json`은 운영 catalog를 SQLite mode=ro로 조회했다.14행(analyses3/datasets6/gmais_idempotency2/gmais_jobs2/models1)이며 저장 Workflow record는 관측되지 않았다. 기존 Job2 및 catalog canonical SHA는 시작 기준과 같다. 이는 새 전달 함수의 실자료 MATCH를 증명하지 않는다. 이 함수의 성공·차단 검증은 격리 합성 자료(TESTED_SYNTHETIC)다. 실제 Workflow 전달·JobPOST·새QA·학습을 실행하지 않았다.

web_ui의 읽기 영향 검토상 기존 Workflow 화면은 계획/정책/입력/계보 진단과 자동 Job 실행 미연결을 표시한다. 이번 신규 순수 함수는 공개 API/UI에 비연결이므로 직접 화면 변경·프론트/브라우저 재시험이 없다. 기존84/85 화면과응답을 보존한다. 후속 수동 연결은 별도 작업 단위로 원 Workflow pin·선택 node·제안 metadata와 stale 상태를 함께 다뤄야 한다.


## 19:40 KST — Workflow 선택 노드 → 제안 Job 입력 전달 계약 검증 완료 (86)

- **workflow_handoff:** 신규 순수 core·시험·문서86 완료/동결. 관련13 PASS/0.058초. 전체 caller Workflow canonical pin 확인 후 선택node의 Agent/capability/Trace·ordered id/version/hash·role/URI 존재를 제안 metadata와 대조한다. URI exactstr 선검사·거대 policy 문자열 상한을 보완했다.
- **catalog_navigation_review:** 최종 독립13 PASS/0.050초, 보완 후 추가결함0. 비선택empty보존/선택empty차단·dependency 중복원형보존·모호node·상충SHA·20false/7IO0·원문불변/privacy를 확인했다. DAG 전체순환은 미검사이며 cycle요청도 전달선언이 같으면 MATCH일 수 있다(dag_validated=false).
- **Root 전체·보존:** backend882개/881 PASS/기존Windows symlink1 SKIP/346.255초/exit0. 최종 소스 보완 직전 시작한 전체시험은 중단하여 별도 interrupted 로그로 보존하고 최종freeze뒤 전체를 다시 실행했다. 최종 PASS만 완료 근거다. 보호141·기존코어48 변경0, 기존추적 code/data/tests/frontend 변경[], catalog14행/기존Job본문 동일이다. 원본·원장·lock·예약136314880B·분할·모델·후보1095/차단4·학습BLOCKED를 보존했다.
- **실환경·UI:** mode=ro catalog에서 저장Workflow record0/기존Job2를 관측했다. 신규함수의 긍정·차단은 TESTED_SYNTHETIC이고 실제 Workflow→Job 전달 검증이 아니다. web_ui 읽기영향검토 결과 공개 API/UI에 비연결인 내부 core로 이번 직접UI 변경·프론트/브라우저 재시험은 없다. 기존84/85 화면/응답 유지. 실제 JobPOST·Registry/파일검사·새 QA/학습·executor 연결0.
- **문서·이해자료:** 신규86 및 관련07/28/40/77·운영원장/소유권/인계서를 갱신했다. understanding_agent에 완료코드·관련/독립/전체·catalog/보존근거를 전달하여 쉬운설명·이론·코드/데이터·발표대본·FAQ·INDEX·변경이력을 같은 단위로 갱신한다. 최종 문서감사와 raw SHA snapshot은 `evidence/integration/workflow-node-handoff-closeout-20261017.json`에 기록한다.
- **범위·다음:** metadata MATCH는 완성Job/AOI/output/선행Result/DAG/출처인증/기관ACL/과학/실행 승인이 아니다. 다음은 GeoQuery planJson 원문을 기준으로 별도 수동API/UI에 연결하는 단위(PLANNED, 구현0). 기존반환 plan.nodes로 원문을 재구성하지 않고 엄격JSON·요청응답hash·canonical교차언어근거·독립상태/세대guard를 설계한다. 전체프로젝트는 미완료이며 계속개발한다. geoai-2 ACTIVE10분은 예약설정으로 실제수집학습worker와 구분한다.

근거: `evidence/integration/workflow-node-handoff-live-integrity-20261017.json`, `evidence/integration/workflow-node-handoff-full-tests-20261017.log`, `evidence/integration/workflow-node-handoff-catalog-observation-20261017.json`.
