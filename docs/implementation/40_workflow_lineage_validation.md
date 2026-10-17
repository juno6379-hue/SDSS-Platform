# Workflow 입력의 현재 전이 계보 진단

## 2026-10-17 — 선택 노드와 제안 Job의 입력 전달 계약(86)

신규 `backend/app/workflow_node_input_handoff.py:compare_workflow_node_input_handoff`는 caller-pinned 전체 Workflow request와 선택 node_id를 제안 Job의 제한된 metadata와 순수 대조한다. agent_id·capability_id·execution_context.trace_id 및 ordered input_refs의 id/version/sha256·role/URI의 부재와 값을 비교한다. pin에는 선택외 node·policy·dependency도 포함되지만 SHA 일치는 신뢰한 원본 인증이 아니다.

이 함수는 전체 Job 생성기/검증기가 아니다. 기존 Workflow 계획·DAG 검사·현재 Registry/파일 진단·79~85의 기존 Job 검증을 호출하거나 대신하지 않는다. 선택외 빈입력은 보존하고 선택node 빈입력만 차단한다. 전체 DAG cycle을 검사하지 않아 선언이 같으면 cycle 포함 요청도 MATCH일 수 있으며 dag_validated=false다. AOI·requested_outputs·선행 Result를 추정하지 않고 Job/Result·실제 executor/학습을 시작하지 않는다. 공개 API/UI 연결은 없고 기존 응답/화면을 유지한다. 세부 지원subset·한도·순수함수 사용법·시험/한계는 [문서86](86_workflow_node_input_handoff.md)에 기록한다.

작성: 2026-10-17, Asia/Seoul. 담당: data_pipeline. `workflow_lineage.py`, `workflow_lineage_api.py`, `test_workflow_lineage.py`를 추가했다. root가 main router를 연결했다. 공통 배치 처리는 `lineage_batch.py`로 추출하고 기존 `job_lineage.py`가 재사용하도록 변경했다. 원문 Workflow schema와 기존 `/v1/workflows/plan` 응답·실행 gate는 변경하지 않았다.

## 상태와 경계

- **TESTED_SYNTHETIC:** 신규 Workflow11시험 및 기존 Job12회귀 통과. 독립 실행도 합계23시험 통과했다.
- **실제 연결:** main app router 배선은 root가 적용했다. 실제 HTTP·UI·전체 회귀 결과는 root의 별도 근거로 확정한다.
- **BLOCKED/미구현:** 과학 승인, 기관 ACL, 실제 Workflow executor, Job/Trace 생성, 실행 시점의 불변 파일 snapshot. 계보 일치만으로 실행하지 않는다.

새 `POST /v1/workflows/lineage-validation`은 원문 WorkflowPlan 본문을 받아 현재 파일의 전이 계보만 검사하는 내부 RFC companion이다. 저장 Job이나 제출 snapshot을 만들거나 수정하지 않는다. 응답은 항상 `mode=PLAN_ONLY`, `status=BLOCKED`, `execution_started=false`, `can_execute=false`다. `authorization_verified`, `execution_authorized`, `scientific_approval`도 false다.

## 요청과 응답 계약

기존 `_workflow_plan_validator()`로 전체 원문 schema를 검사한다. 중복 node ID, 없는 dependency, 자기 의존, cycle은 고정 오류로 거부한다. 반복 dependency는 기존 계약처럼 set으로 정규화하며 node ID의 공백은 임의로 제거하지 않는다. 전체 DAG 선검증을 통과한 요청만 Dataset 해시 검사에 도달한다. 노드 수 한도 초과는 DAG 계산 전에 별도 한도 진단으로 종료한다.

| 필드 | 의미 |
|---|---|
| `extension` | `greenblue.workflow-lineage-validation.rfc1` |
| `approval_status` | `INTERNAL_REVIEW` |
| `present_in_upstream_openapi` | false. 승인된 원문 표준 경로가 아님 |
| `evaluation_scope` | `CURRENT_WORKFLOW_TRANSITIVE_LINEAGE_PLAN_ONLY` |
| `workflow_run_id`, `trace_id` | schema에 맞는 요청의 신원 |
| `request_sha256` | 실제 수신 HTTP 본문 bytes의 SHA256 |
| `assessment_started_at`, `assessment_finished_at` | UTC 현재 검사 시각. 데이터 취득·갱신 시각이 아님 |
| `available`, `reason` | 보고서 제공 가능 여부와 `CURRENT_LINEAGE_CHECKED` 또는 `CHECK_LIMIT_REACHED` |
| `dag_validated`, `topological_order` | 전체 DAG 검증 여부와 결정적인 위상 순서 |
| `bindings` | `{node_id,input_index,ref:{id,version,sha256},diagnostic_index,reused,checked}` |
| `diagnostics` | Dataset API의 allowlist projection을 재사용한 개별 root 계보 진단 |
| `nodes` | 원문 순서의 `{node_id,bindings,blockers,inputs_complete,status,execution_authorized}` |
| `blockers` | `{node_id,input_index,code}`. 전체 한도 차단은 신원 index가 null |
| `limits` | 서버 상한과 실제 검사량 |

`request_sha256`는 canonical JSON이나 재직렬화 결과의 해시가 아니다. 공백·줄바꿈·숫자 표기가 다르면 다른 해시다. UI는 실제 전송할 `JSON.stringify(parsedPayload)`의 UTF8 bytes를 WebCrypto로 해시해 요청과 응답을 대조한다. 서버는 수신 bytes에서 JSON을 파싱하고 NaN/Infinity/-Infinity 같은 비표준 상수는 거절한다. 본문 자체는 반환하지 않는다.

`checked=true`는 해당 root 진단을 수행했거나 같은 요청에서 재사용했다는 뜻이며 성공을 뜻하지 않는다. 미검사는 `checked=false`, `diagnostic_index=null`이다. 입력이 빈 node에는 `INPUT_REFS_REQUIRED`, `inputs_complete=false`를 명시한다. 모든 node 입력 계보가 일치할 때만 `lineage_integrity_verified=true`이며 그래도 운영 `status=BLOCKED`와 비실행 플래그는 유지한다. 개별 진단의 `INTEGRITY_VERIFIED`는 Workflow 실행·권한·과학 승인이 아니다.

URI/role/parameters·registry manifest 경로·자격정보·내부 예외를 출력하지 않는다. 고정 ref의 id/version/SHA는 binding 식별에 필요한 범위로만 반환한다. 비PUBLIC root 또는 조상의 기관 ACL이 연결되지 않으면 차단하고 제한 조상의 추가 lineage를 조회·노출하지 않는다. 요청 URI hint를 파일 경로로 사용하거나 네트워크에서 자료를 가져오지 않는다.

## Workflow 전체 한도와 재사용

기본 상한은 node128개, 입력 ref64개, 고유 root32개, root 깊이32, root당64 node, 전체256 node 검사다. Python 내부 keyword는 이 범위 이하로만 설정하며 bool·범위 초과를 거부한다. HTTP 본문에 임의 한도 확장 필드를 추가하지 않는다.

- node128 초과: `WORKFLOW_NODE_LIMIT`, `available=false`, `dag_validated=false`, 빈 bindings/diagnostics/nodes.
- DAG 검증 후 ref64 또는 고유 root32 초과: `WORKFLOW_INPUT_REF_LIMIT` 또는 `WORKFLOW_UNIQUE_ROOT_LIMIT`, `available=false`, `dag_validated=true`, 빈 bindings/diagnostics/nodes. 해시 검사는 없다.
- 같은 `(id,version)`의 다른 SHA: node가 달라도 `WORKFLOW_INPUT_REFERENCE_CONFLICT`로 해당 양쪽 binding을 무해시 차단한다. 동일 Dataset의 서로 다른 고정 version은 허용한다.
- 같은 고정 `(id,version,sha256)` root는 node를 넘어 같은 요청 안에서 한 번만 검사하고 `diagnostic_index`를 공유한다. 요청 간 캐시는 없다.
- 서로 다른 root가 공유하는 조상을 각각 검사하면 그 반복 작업도 실제 반환 nodes 수로 합산한다. `node_checks_performed`는 그 합이며 `unique_roots_checked`는 수행한 root 진단 수다.
- 남은 전체 예산과 root당 한도 중 작은 값으로 다음 root를 검사한다. 예산0 뒤 새 root는 `WORKFLOW_TOTAL_NODE_CHECK_LIMIT`으로 미검사를 명시하고 코어를 호출하지 않는다. 이미 검사한 동일 root 캐시는 이후에도 재사용한다.

부분 검사 보고서는 `available=true`, `reason=CHECK_LIMIT_REACHED`일 수 있다. 구조적 SHA 충돌만 있는 보고서도 `available=true`, 빈 diagnostics, `current_assets_revalidated=false`가 정상이다. available을 검증 성공이나 전체 검사 완료로 해석하지 않는다. `current_assets_revalidated`는 하나 이상의 개별 진단에서 실제 resolve 시도가 있었는지를 뜻한다.

한도는 파싱된 요청의 그래프·참조·node 검사량을 제한한다. HTTP 본문 크기·개별 artifact 총 bytes·운영 동시부하의 상한을 제공하지 않는다. 검사 중 파일을 순차 읽으므로 전체 그래프의 원자적 snapshot이나 검사 후 불변성을 보장하지 않는다.

## HTTP·비쓰기·기존 Job 호환

schema/DAG/JSON 오류는400 `INVALID_REQUEST`의 고정 메시지다. jsonschema의 원문값 포함 예외를 반사하지 않는다. 내부 검사 오류는503 `RESOURCE_UNAVAILABLE`이며 내부 ValueError를 요청400으로 잘못 분류하지 않는다. 자료 미등록·동적 version·SHA·계보·ACL 차단은200 진단이다. 응답·오류에 `Cache-Control:no-store`를 적용한다. 실제 main app의 token dependency를 상속해401을 확인했으며 이는 기관별 자료 ACL 승인을 뜻하지 않는다. 파일 해시는 `run_in_threadpool()`에서 실행한다.

`lineage_batch.py`는 Job/Workflow의 고정 ref 캐시·예산·projection만 공유한다. 가짜 Job을 생성하지 않는다. 기존 Job identity/legacy 검사와 저장 snapshot 경로는 유지했다. 정상·부분 예산 이후 캐시·SHA 충돌 3가지 Job 응답 전체를 추출 전후 비교해 완전히 같음을 확인했다. 근거는 `evidence/integration/job-lineage-shared-refactor-baseline-20261017.json`이다. 원문 schema와 기존 `/v1/workflows/plan` 응답도 유지했다.

## 시험 근거

```powershell
$env:PYTHONPATH = "$PWD/.runtime;$PWD/backend;$PWD/tests"
$env:PYTHONIOENCODING = 'utf-8'
python -m unittest discover -s tests -p test_workflow_lineage.py -v
python -m unittest discover -s tests -p test_job_lineage.py -v
```

신규 **11 PASS / 1.995초**: [Workflow 로그](../../evidence/integration/workflow-lineage-tests-20261017.log). 기존 Job **12 PASS / 4.066초**: [공유 추출 회귀 로그](../../evidence/integration/job-lineage-shared-refactor-tests-20261017.log). schema/DAG hash0, node129·ref65·unique33 선차단, cross-node cache/충돌, 서로 다른 version, 전체 예산 소진 후 cache 재사용, 빈 입력·partial mapping, missing/dynamic/ACL, 매요청 자산 재검사, exact raw body SHA, NaN/Infinity 거절, 민감 원문 비노출, main token401/200, 기존 plan 응답, Store/source/SQLite 바이트 불변 및 Job/Trace 비생성을 확인했다.

독립 담당도 Workflow11+Job12 **23 PASS / 5.134초 / 종료0**를 확인했다. [독립 로그](../../evidence/integration/workflow-lineage-independent-tests-20261017.log). 별도 적대 fixture에서 cross-node 예산·캐시·partial mapping, SHA 충돌 무해시, 제한 조상 비노출, cycle 선차단, raw SHA/NaN400 및 원본 불변을 확인했으며 추가 재현 결함은 없었다. 위 관련 시험 수를 과거 전체 회귀와 합쳐 통합 수치를 추정하지 않는다.

## UI 인계와 남은 범위

web_ui에 wrapper·raw SHA·limits·binding/node 매핑·빈 입력·부분검사·available 의미를 인계했다. GeoQuery에서 명시적 버튼으로 현재 계보를 검사하고 기존 plan 결과와 구분한다. 자동 조회·폴링이나 실행 gate 해제는 없다. 본문 변경·요청 경합 시 이전 보고서를 제거하고 실제 전송 bytes SHA를 대조한다. UI 구현·브라우저 근거는 담당 문서41과 root의 별도 증거를 따른다.

원문 Workflow의 시간/AOI/product 의미 검증, 과학 검증, 기관 권한, 실행 시점 자료 고정, 실제 executor·배포 승인은 후속 범위다. 이번 내부 companion 구현을 전체 프로젝트 완료나 과학·실행 승인으로 보고하지 않는다.


## Root 최종 통합·실제 읽기 근거

전체 scripts/test.ps1 **321건/320PASS/1SKIP/72.556초·종료0**, workflow-lineage-full-tests-20261017.log. UI66modules19.37초·38PASS961.1713ms. 실제UI5174→API8002의공유미등록2참조+빈입력1노드요청에서진단1/검사1/동일ref재사용·빈입력차단·PLAN_ONLYBLOCKED·rawbodySHA대조확인,cycle400/NaN400/no-store. 기존계획API/정책·입력카드FAIL_ALL/PLAN_ONLYBLOCKED유지. desktop/mobile·초안823자정확복원·입력변경clear는문서41및workflow-lineage-live-20261017.json/screenshots근거. 보호5SHA와기존2Job레코드SHA불변/신규실행0. 실제성공계보·운영승인증거가아니다.

### 107 의존 순서 공통화

기존 Kahn sorted-ready-layer 순서만 순수 helper로 공통화했다. caller의 검증 우선순위·오류·응답·Store/manifest 접근·승인 제한은 유지한다. 내부 구현·입력 전제·회귀 근거와 한계는 [107 구현 문서](107_workflow_dependency_order.md)를 따른다. UI·API 추가나 실제 실행 승인이 아니다. 전체·독립·보존 근거: `evidence/integration/workflow-dependency-order-live-integrity-20261017.json`. 이해자료와 인계서도 같은 단위로 갱신했다.
