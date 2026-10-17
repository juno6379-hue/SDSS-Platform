# Workflow 노드의 고정 입력 연결

## 2026-10-17 — Agent·capability 등록관계 공통 검사(93)

`agent_capability_contract.agent_capability_issue(agent, capability_id)`는 이미 선택된 내부 manifest의 부재/등록capability membership만 검사한다. Job 제출과 Workflow 계획의 중복검사를재사용하되 Job의firstmatch·Workflow의lastduplicate 선택·HTTP코드/문구·readiness·Store접근순서·멱등동작을그대로둔다. 원문모듈 SHA핀과격리임시Store를사용해 기존전체응답/헤더·레코드·접근순서동등성을검증한다.

이함수는Registry를읽거나 모델/기관ACL/과학·실행을승인하지않는다. trusted내부manifest 전제가있으며새validation/normalization정책을추가하지않아잘못된manifest의기존예외도보존한다. 기존89/90/91 fullJob검토에는연결하지않고24false·agent_capability_verified=false·날짜검사92를보존한다. 공개API/화면계약변경이없어직접frontend/build/브라우저재시험은없으며운영JobPOST는하지않았다. 계약·시험·한계는 [문서93](93_agent_capability_contract.md)를참조한다.

## 2026-10-17 — 선택 노드와 제안 Job의 입력 전달 계약(86)

신규 `backend/app/workflow_node_input_handoff.py:compare_workflow_node_input_handoff`는 caller-pinned 전체 Workflow request와 선택 node_id를 제안 Job의 제한된 metadata와 순수 대조한다. agent_id·capability_id·execution_context.trace_id 및 ordered input_refs의 id/version/sha256·role/URI의 부재와 값을 비교한다. pin에는 선택외 node·policy·dependency도 포함되지만 SHA 일치는 신뢰한 원본 인증이 아니다.

이 함수는 전체 Job 생성기/검증기가 아니다. 기존 Workflow 계획·DAG 검사·현재 Registry/파일 진단·79~85의 기존 Job 검증을 호출하거나 대신하지 않는다. 선택외 빈입력은 보존하고 선택node 빈입력만 차단한다. 전체 DAG cycle을 검사하지 않아 선언이 같으면 cycle 포함 요청도 MATCH일 수 있으며 dag_validated=false다. AOI·requested_outputs·선행 Result를 추정하지 않고 Job/Result·실제 executor/학습을 시작하지 않는다. 공개 API/UI 연결은 없고 기존 응답/화면을 유지한다. 세부 지원subset·한도·순수함수 사용법·시험/한계는 [문서86](86_workflow_node_input_handoff.md)에 기록한다.

기준: 2026-10-17 KST. 내부 RFC·계획 검사 기능이며 실제 DAG 실행과 구별한다.

## 입력에서 진단까지

`POST /v1/workflows/plan`은 원문 Workflow Plan schema와 node ID·의존성·cycle을 먼저 확인한다. 유효하지 않은 DAG는 Registry 조회나 자산 해시 검사를 시작하지 않는다. 유효한 DAG에서는 `gmais_api.py:plan_workflow`가 각 노드의 `input_bindings`를 기존 `job_inputs.resolve_job_inputs(store, refs)`에 전달한다.

이전에는 입력이 있어도 Registry adapter가 없다는 `DATA_MISSING`을 무조건 반환했다. 이제 등록한 PUBLIC·VALIDATED 자산의 ID/version/실파일 SHA/URI가 맞으면 해당 입력 사유를 제거한다. 하지만 기존 Agent·모델 gate와 실행기 미연결 사유를 유지해 node와 전체 Workflow는 BLOCKED다.

## 응답과 사용법

기존 Workflow 요청 형식은 변경하지 않는다. 각 `nodes[].input_resolution`에 다음을 추가한다.

- `extension=greenblue.workflow-input-resolution.rfc1`, `approval_status=INTERNAL_REVIEW`.
- `evaluated_at`은 이번 요청의 검사 시각이며 `evaluation_scope=PLAN_REQUEST_SNAPSHOT_NOT_EXECUTION_AUTHORIZATION`이다.
- `resolved`는 입력 순서대로 진단하며 `blockers`는 코어의 상세 코드와 입력 인덱스를 담는다.
- node의 `blockers`에는 기존 표준 오류 분류를 유지하고 `detail_code`와 `input_index`를 추가한다. 누락/빈입력은 DATA_MISSING, ACL 미연결은 FORBIDDEN, Registry 오류는 RESOURCE_UNAVAILABLE, 참조/URI 충돌은 SCHEMA_MISMATCH, 나머지 무결성·품질 오류는 DATA_QUALITY다.
- node의 `execution_authorized`, 전역 `can_execute`·`execution_started`는 항상 false다. mode는 PLAN_ONLY다.

같은 Dataset ID의 다른 고정 version을 T1/T2로 사용할 수 있다. 동일(id,version)에 상충 SHA가 있으면 해당 노드에서 차단한다. 다른 노드의 입력을 한 목록으로 합치지 않아 노드 사이에 가짜 중복 충돌을 만들지 않는다. `input_integrity_verified=true`라도 RAW·RESTRICTED/CONFIDENTIAL 등의 blocker가 있으면 입력 승인으로 읽지 않는다. 제한자료의 경로·URI·원문 manifest·예외문구는 진단에 노출하지 않는다.

Workflow plan은 Job의 Idempotency 재생과 다르게 **매 요청 현재 파일을 다시 검사**한다. 같은 workflow_run_id/trace_id를 다시 사용해도 파일 변경을 새로 발견할 수 있다. 이 endpoint는 계획을 영속 저장하거나 중복 Job을 생성하지 않는다. 실제 실행 직전 재검증은 별도로 필요하다.

## 검증과 재현

```powershell
.\scripts\test.ps1
```

회귀시험은 `tests/test_gmais_workflow_extension.py`의 임시 Store·명시적 계약 fixture를 사용한다. 관련14건 PASS/3.910초, `evidence/integration/workflow-input-tests-20261017.log`. 기존7건과 신규7건이며, DAG 선검증·정상/실패 입력·품질/접근 차단·버전 비교·파일 변경 재검사·Agent READY 강제 시 비실행·원본/카탈로그 바이트 불변·Job/Result/Trace 미생성을 확인했다. 독립 검토에서 추가 재현 결함이 없었다.

신규 코드 포함 전체 `scripts/test.ps1` 회귀는 **247건 중246 PASS/1 SKIP,139.318초·종료0**이다. 보존 로그는 `evidence/integration/workflow-input-full-tests-20261017.log`다. SKIP은 기존 Windows 실제 symlink 생성권한 부족 시험이며 deterministic 경계 시험은 통과했다. 관련14건은 전체 결과에 포함되므로 별도 합산하지 않는다. 기존 실자료 카탈로그·원장·lock·분할·모델을 변경하거나 수집·학습을 시작하지 않는다. 기존 API 프로세스를 재시작하지 않으므로 새로운 HTTP 동작의 검증 범위는 TestClient다.

## 남은 범위

후속으로 계획 단계의 차단 원인 전파 진단을 [문서29](29_workflow_blocking_policy.md)에 구현했다. [화면 인계 기록](30_workflow_diagnostics_ui.md)에서 실제 표시·실행 서버 연결 근거를 구분한다. 아래 상태 전파/정책 실행의 남은 범위는 실제 실행 엔진에 대한 것이다.

실제 DAG 스케줄링, 의존노드 상태 전파, STOP_DEPENDENTS/FAIL_ALL 실행, timeout/retry/cancel, 승인 모델·기관 ACL·자료 의미 적합성(AOI/기간/제품), 노드 출력→다음 입력의 동적 바인딩과 Result 생성은 후속이다. 현재 depends_on/topological_order 검사를 실행 엔진으로 설명하지 않는다. 원문 GMAIS schema/OpenAPI와 기관 승인 상태는 변경하지 않는다.

### 107 의존 순서 공통화

기존 Kahn sorted-ready-layer 순서만 순수 helper로 공통화했다. caller의 검증 우선순위·오류·응답·Store/manifest 접근·승인 제한은 유지한다. 내부 구현·입력 전제·회귀 근거와 한계는 [107 구현 문서](107_workflow_dependency_order.md)를 따른다. UI·API 추가나 실제 실행 승인이 아니다. 전체·독립·보존 근거: `evidence/integration/workflow-dependency-order-live-integrity-20261017.json`. 이해자료와 인계서도 같은 단위로 갱신했다.
