# Workflow 계획의 의존성 차단 원인

기준: 2026-10-17 KST. 내부 RFC·순수 진단 기능이다. 실제 DAG 실행·취소·retry를 수행하지 않는다.

## 문제와 처리

노드 자신의 입력/Agent 차단과, 선행 노드 때문에 진행할 수 없는 원인을 구분한다. `workflow_policy.diagnose_workflow_blocking(reviewed_nodes, policy)`는 Store·파일·네트워크에 접근하지 않고 local blockers의 snapshot을 DAG에 전파한다. 원문 policy의 알려진 on_blocked enum만 해석하며 max_parallel·require_human_approval로 실행 권한을 만들지 않는다.

- STOP_DEPENDENTS: 실제 ancestor 중 local blocker가 있는 노드만 `upstream_blocked_by`로 표시한다. 독립 분기의 차단을 전파하지 않는다.
- FAIL_ALL: 실제 upstream 원인은 그대로 두고, 실제 ancestor가 아닌 다른 노드(자기 제외)의 local blocker를 `policy_blocked_by`에 추가한다. 자기 자신은 정책/선행 원인에 중복 표시하지 않는다.
- `blocking_cause_node_ids`는 자기 local·upstream·정책 원인의 합집합이다. diamond·반복 depends_on은 중복 원인을 만들지 않는다.
- node ID·원인 목록·local blocker 복사본을 결정적으로 정렬하고 원본 입력은 변경하지 않는다. 중복 node ID·없는 dependency·자기 의존·cycle·잘못된 정책은 거부한다. 원문 schema가 허용하는 반복 dependency와 opaque ID는 보존한다.

## API 연결과 상태

`POST /v1/workflows/plan`은 기존 schema/DAG 검증과 노드별 입력 진단을 먼저 수행한다. 전파 계산은 그 시점 local blockers만 seed로 쓰며 전파 결과를 다시 seed에 섞지 않는다. 응답의 `policy_resolution`은 내부 RFC `greenblue.workflow-blocking-policy.rfc1`과 진단 전체를 담고, 기존 순서의 각 `nodes[].dependency_resolution`에 해당 노드 진단을 연결한다. 기존 node.blockers와 status는 유지한다.

`diagnostic_status=NO_BLOCKING_CAUSE_IDENTIFIED`는 READY가 아니다. 모든 `execution_authorized=false`, 전역 PLAN_ONLY/BLOCKED·can_execute=false·execution_started=false를 유지한다. 실제 Agent는 현재 모두 차단 상태이므로 두 정책 차이는 node.status 변화가 아니라 원인 범위로 나타난다. 깨끗한 독립 분기는 순수 코어 fixture에서만 만들어 검증한다.

## 검증

코어9 PASS/0.011초, `evidence/integration/workflow-policy-core-tests-20261017.log`. 결정성·순서 변경·diamond·다중 원인·입출력 깊은 복사·유효하지 않은 graph/정책을 확인했다. API20 PASS/6.965초, `workflow-policy-api-tests-20261017.log`에서 표준 schema·원래 blocker/노드 순서·정책별 원인·비실행/비저장을 검증했다.

신규 코드 포함 `scripts/test.ps1` 전체 실행은 **262건 중261 PASS/1 SKIP,85.881초·종료0**다. 로그 `evidence/integration/workflow-policy-full-tests-20261017.log`. SKIP은 기존 실제 OS symlink 생성권한 시험이며 deterministic 경계 시험은 통과했다. UI 어댑터10 PASS와 production build는 별도 프론트 검증이며 이 백엔드 총수에 합산하지 않는다.

## UI 인계와 남은 범위

UI에는 입력 진단과 함께 local/선행/정책 차단 원인을 표시하도록 인계한다. [화면 반영 기록](30_workflow_diagnostics_ui.md)은 UI 담당 작업 완료 후 최종 근거가 된다. 테스트 API와 실행 중 서버 적용을 구분하고 브라우저에서 실제 응답·표시를 확인한다.

UI 담당이 공통 진단 카드·메뉴 연결을 구현하고 adapter10 PASS·build52modules/18.95초를 확인했다. Root는 새 UI5174의 동일출처 proxy→API8001에서 두 정책의 실제 표시를 확인했다. `workflow-policy-live-ui-20261017.json`과 문서30의 최종 절을 따른다. 기존 서버 중지 명령은 자동 검토에서 차단되어8000/5173을 보존했고, 신규 개발 환경에서 안전하게 검증했다.

실제 scheduler·정책 실행·상태 영속화·retry/timeout/cancel·동적 출력 바인딩·기관 ACL·과학 및 배포 승인은 후속이다. max_parallel을 지키며 작업을 실행하거나 FAIL_ALL로 실행 중 작업을 취소한 것으로 설명하지 않는다.

### 107 의존 순서 공통화

기존 Kahn sorted-ready-layer 순서만 순수 helper로 공통화했다. caller의 검증 우선순위·오류·응답·Store/manifest 접근·승인 제한은 유지한다. 내부 구현·입력 전제·회귀 근거와 한계는 [107 구현 문서](107_workflow_dependency_order.md)를 따른다. UI·API 추가나 실제 실행 승인이 아니다. 전체·독립·보존 근거: `evidence/integration/workflow-dependency-order-live-integrity-20261017.json`. 이해자료와 인계서도 같은 단위로 갱신했다.
