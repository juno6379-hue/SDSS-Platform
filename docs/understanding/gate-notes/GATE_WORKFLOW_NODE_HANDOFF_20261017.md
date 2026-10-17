# Gate Workflow Node Handoff 20261017 — 선택 노드와 제안 입력의 순수 대조

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | Git 연결됨; 문서 작성 시 변경분 미커밋, evidence snapshot SHA로 추적 (원격 기준 d483d25) |
| evidence_paths | `backend/app/workflow_node_input_handoff.py`; `tests/test_workflow_node_input_handoff.py`; `docs/implementation/86_workflow_node_input_handoff.md`; `evidence/integration/workflow-node-handoff-related-20261017.log`; `evidence/integration/workflow-node-handoff-independent-20261017.log`; `evidence/integration/workflow-node-handoff-full-tests-20261017.log`; `evidence/integration/workflow-node-handoff-live-integrity-20261017.json`; `evidence/integration/workflow-node-handoff-catalog-observation-20261017.json`; `evidence/integration/workflow-node-handoff-runtime-start-20261017.json`; `evidence/integration/workflow-node-handoff-full-interrupted-before-final-freeze-20261017.log` |
| confidence | 완료 코드와 격리 합성 시험; 실제 Workflow 전달·실행은 미검증 |
| status | TESTED_SYNTHETIC; API·UI·executor 미연결; 전체 개발 진행 중 |

## 쉬운 설명

전체 작업 지시서에서 한 작업의 재료 목록을 골라 전달 초안과 비교한다. 담당자와 작업 종류, 추적 번호, 재료의 순서와 버전이 그대로인지 본다. 메모가 빠진 것과 빈 메모가 있는 것도 구분한다. 두 목록이 같다는 결과는 작업 지시서 전체가 실행 가능하거나 재료 파일이 검증됐다는 뜻은 아니다.

## 이론적 배경

기존 Workflow 계획은 노드 입력을 진단하지만 선택 노드가 제안 Job metadata로 옮겨지는 선언 경계는 별도다. 새 함수는 호출자가 고정한 전체 Workflow 요청의 지문을 확인한 뒤 선택 노드의 선언과 제안을 비교한다. 선택하지 않은 노드·정책·dependency도 전체 pin에 들어가므로 다른 부분이 바뀐 요청을 같은 요청으로 사용하지 않는다.

이는 전달 선언의 동등성이다. caller가 요청과 pin을 함께 제공하므로 원본 출처 인증이나 운영 저장 증거가 아니다. Job을 만들거나 기본 AOI·output·선행 Result를 추정하지 않는다. 완성 Job의 유효성 검사도 아니다.

## 코드와 데이터 동작

`compare_workflow_node_input_handoff(workflow_request, pinned_workflow_request_sha256, selected_node_id, proposed_job_metadata)`는 순수 함수다. Workflow schema 0.2.0의 지원 subset을 엄격 검사한다. 전체 node 1..128개, 전체 입력 합계 최대64개, 문자열 최대256자다. policy는 알려진 키만 허용하고 정수는 bool과 구분한다. timeout/max_parallel의 int32 상한 등 원 schema보다 좁은 범위를 지원한다.

전체 구조와 scalar를 검사한 뒤 Python sort_keys·compact UTF8 직렬화 SHA를 caller pin과 비교한다. dict 삽입 순서는 무관하지만 배열 순서·선택 필드의 존재·dependency 중복 원형은 보존한다. RFC8785나 입력 파일의 raw bytes SHA가 아니다.

선택 노드의 agent_id/capability_id와 Workflow trace_id, ordered input_bindings를 제안의 네 필드 agent_id/capability_id/execution_context/input_refs와 비교한다. 입력 id/version/sha256과 선택 role/uri의 존재·값을 모두 본다. 부재와 명시 빈 URI는 다르고, 양쪽의 빈 URI는 이 선언 계약에서 일치할 수 있다. 이것이 실제 resolver의 URI 지원을 보장하지는 않는다.

같은 id의 다른 version은 가능하지만 같은(id,version)의 다른 SHA 선언은 전체 Workflow와 제안 안에서 각각 차단한다. 선택하지 않은 노드의 빈 입력은 허용하고 선택 노드의 빈 입력은 차단한다. 미등록 dependency와 자기 참조·중복 node ID는 거부한다. 그러나 다중 노드 순환 전체는 검사하지 않는다.

## 시험 증거

최종 관련 13 PASS/0.058초·독립 13 PASS/0.050초다. URI는 exact str 검사 후 빈 값 equality를 평가하고, 거대 on_blocked는 enum 비교 전에 문자열 상한으로 차단한다. 합성 fixture로 MATCH·입력 원형 불변·open 금지·privacy·20false/7IO0, 전체 pin 변경, 각 필드 차이, 순서·role/URI 부재·빈 URI, 같은 id의 다른 version, 상충 SHA, 선택 node·전체 예산·typed scalar·재귀 container·dependency 원형을 검증했다.

두 노드가 서로 의존하는 순환이어도 선언이 같으면 MATCH가 될 수 있는 회귀가 있다. dag_validated=false를 유지하는 의도된 검사 범위다. 독립 최종 13개 반복은 전체에 합산하지 않는다. 수정 전 전체 회귀는 중단 로그로 보존됐으며 완료 근거가 아니다. 최종 freeze 뒤 전체 회귀는 882건 중 881 PASS·기존 Windows symlink 권한 제약 1 SKIP, 346.255초·종료 0으로 완료했다. 실제 Workflow executor나 운영 Job 전달을 관측한 것이 아니다.

## 한계와 승인

20개 승인·검증 flag는 false이고 네트워크·파일 읽기/쓰기·DB·Registry·resolver·executor의 7개 계수는 정수0이다. 이 순수 함수의 범위이며 이후 연결하는 전체 경로의 IO0을 보장하지 않는다. 입력은 이미 메모리에 있으므로 HTTP body byte·전체 CPU·RAM hard cap도 아니다.

현재 파일·Registry·전이 계보·기관 권한·과학·모델 준비도·AOI·output·predecessor·DAG·실행기 전달을 검증하지 않는다. MATCH로 기존 Workflow PLAN_ONLY/BLOCKED나 원본5차단·후보4차단을 해제하지 않는다. 공개 API·UI·Job POST·실행 체인을 바꾸지 않아 직접 UI 수정·프론트 재시험·브라우저 검사는 없다. 기존84/85 화면은 그대로다.

## 1분 발표

“전체 Workflow에서 선택한 작업의 입력 목록이 전달 초안에 그대로 옮겨졌는지 비교했습니다. 담당 Agent와 작업 종류, 추적 번호, 파일 선언의 버전·지문·순서를 확인합니다. 선택 메모가 없는 것과 빈 메모가 있는 것도 나눕니다. 다만 이것은 목록 대조입니다. 실제 파일을 읽거나 Job을 만들지 않고 작업 순환이나 선행 결과도 검사하지 않습니다. 목록이 같아도 실행·학습·과학 승인은 모두 별도이며 화면과 실행기에는 아직 연결하지 않았습니다.”

## 5분 발표 순서

1. **0~1분:** 전체 작업 지시서와 한 작업의 전달 초안 비유를 말한다.
2. **1~2분:** 전체 요청 pin과 선택 노드의 네 필드 metadata를 설명한다.
3. **2~3분:** 입력 순서·버전·role/URI 부재와 빈 값의 차이를 설명한다.
4. **3~4분:** 합성 시험과 순환이어도 MATCH 가능한 범위를 구분한다.
5. **4~5분:** 파일 IO0·20false, Job 생성·API·UI·실행 미연결을 말한다.

10분 설명에서는 전체128node/64refs subset, int32 정책 상한, 재귀 객체 선검사, 선택 외 노드까지 포함한 pin과 안전 issue/index를 추가한다.

## Q&A

**MATCH면 Workflow가 실행 가능한가?** 아니다. 선택 입력의 전달 선언만 같다는 뜻이며 DAG도 검사하지 않는다.

**앞 작업의 결과를 자동 입력으로 넣나?** 넣지 않는다. predecessor Result의 추정이나 결합은 범위 밖이다.

**URI가 비어도 통과하나?** 양쪽에 명시 빈 URI가 같으면 선언 대조는 가능하다. 실제 파일 위치나 resolver 지원을 보장하지 않는다.

**왜 전체 요청을 고정하나?** 선택하지 않은 노드나 정책이 바뀐 요청을 같은 Workflow로 사용하지 않기 위해서다. 원본 인증은 별도다.

**기존 화면에서 실행되나?** 내부 순수 함수이며 API·화면·Job 생성·실행기에 연결하지 않았다.

## 이후 갱신

독립·전체 회귀·보존 근거를 읽고 INDEX·변경 이력·계약·Orchestrator·구조·용어·발표·FAQ·시연을 함께 갱신했다. 다음은 PLANNED다. GeoQuery의 원문 planJson과 명시 node, 사용자가 제안한 metadata를 별도 수동 API/UI child로 연결할 계획이다. 요약 plan.nodes를 재구성하지 않고 전체 원요청을 사용한다. strict JSON·크기/깊이·언어 간 canonical golden·응답의 전체 요청 결속·입력/선택/route 세대 폐기를 검토한다. caller 선언 pin은 출처 인증이 아니며 아직 이 API/UI의 구현과 실제 관측은 없다. 전체 개발과 10분 보고는 계속된다.


## 실제 환경 관측의 범위

읽기 전용 카탈로그에는 14기록(analyses3·datasets6·idempotency2·Job2·model1)이 있고 시작 시 canonical SHA와 같았다. 저장 Workflow 기록은 0이었다. 이는 환경과 보존의 관측이며 새 handoff의 실자료 positive 검증이 아니다. 새 함수의 상태는 TESTED_SYNTHETIC을 유지한다. 운영 API·Job POST·Workflow 전달·executor·새 QA·학습은 없다.


## 최종 회귀와 보존

최종 전체 backend 회귀는 **882건 중 881 PASS·기존 Windows symlink 권한 제약 1 SKIP**, 346.255초·종료 0이다. 기존 deterministic 경계시험은 통과했다. 관련13/0.058초·독립13/0.050초의 반복과 실제 환경 관측을 전체 시험에 더하지 않는다. 수정 전 중단 로그는 이 완료 결과와 별도로 보존했다.

시험 종료 후 보호 참조141개·기존 코어48개·카탈로그14기록·기존 Job2개 본문이 같았다. 기존 추적 코드·데이터·시험·프론트 변경 목록도 비어 있다. 이는 지정한 보존 범위이며 전체 워크스페이스나 원자 snapshot 보장은 아니다.

새 함수의 근거는 TESTED_SYNTHETIC이다. 운영 카탈로그 관측을 전달 성공이나 원본 인증으로 바꾸지 않는다. 새 API·Job POST·QA·학습·executor 연결은0이며 직접 UI 변경·프론트 재시험·브라우저 검사는 없다. 원본5차단·후보4차단과 기존84/85 화면은 유지한다.
