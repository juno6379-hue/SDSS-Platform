# 저장된 Job 입력 진단 조회

## 2026-10-17 저장 제출 binding 조회 companion (79/80)

`GET /v1/jobs/{job_id}/execution-input-binding`은 저장 Job 1건에서 제출 당시 별도 capture를 안전하게 투영하는 내부 RFC다. 기존 Job Status·input-resolution·현재 계보 API와 구별한다. 현재 Registry·파일·실행자의 입력을 재검사하거나 과거 Job에 capture를 역채우지 않는다. 응답은 RECORDED/UNAVAILABLE/LEGACY/INVALID와 request_job_sha256·안전한 입력/핀 계수·전체 binding 집계 SHA만 제공하고 개별 ID·역할·manifest pin·URI/경로·원문/예외를 반환하지 않는다. 12개 승인 및 현재파일 재검증/실행자 대조는 모두 false다.

한도·타입·Job/Agent/Trace 및 요청 참조 순서/역할 presence·canonical digest를 대조한다. 손상된 Job은 capture 부재보다 우선 INVALID이며, 미기록 null을 0개로 바꾸지 않는다. 단일 store.get을 threadpool에서 수행하고 no-store·기존 인증을 상속한다. 고정 404 JOB_NOT_FOUND / 503 RESOURCE_UNAVAILABLE 오류는 비재시도 선언이며 내부 예외를 노출하지 않는다.

실제 API8002의 기존 legacy Job2건은 LEGACY, 원상태 응답과 동일하고 catalog14행 전후 SHA 불변이다. 추가 없는 Job404 및 257자 요청 INVALID를 포함8GET만 수행했으며 실제 새 Job POST/소급 capture/실행0이다. 근거: `evidence/integration/stored-binding-capture-live-api-20261017.json`. RECORDED 생성은 합성시험 범위이고 운영 환경 관측으로 표현하지 않는다. 수동 UI·실제 브라우저/최종 회귀 검증 결과는 [문서79](79_stored_binding_capture_api.md)·[문서80](80_stored_binding_capture_ui.md)에 기록한다. upstream 확정 표준/학습 준비/과학·기관 권한 승인이 아니다.

기준: 2026-10-17 KST. 내부 읽기 전용 RFC이며 Job Status 원문 schema를 확장하지 않는다.

## 문제와 계약

기존 UI는 Job 제출409 응답에서만 입력 진단을 읽었다. 다시 Job ID로 조회하면 표준 status만 반환되므로 제출 때 저장한 입력 점검을 확인할 수 없었다. 새 `GET /v1/jobs/{job_id}/input-resolution`은 별도 companion 응답으로 저장 snapshot을 제공한다.

반환은 `extension=greenblue.job-input-snapshot.rfc1`, `approval_status=INTERNAL_REVIEW`, job_id·trace_id·available·reason·snapshot을 포함한다. current_files_revalidated·execution_authorized·scientific_approval는 항상 false다.

- RECORDED_SNAPSHOT: 저장 기록이 있고 형식·Job/Trace/입력 참조 연결을 확인해 allowlist 필드만 반환한다.
- LEGACY_SNAPSHOT_NOT_RECORDED: 이전 Job에 snapshot이 없다. HTTP200/available=false/snapshot=null로 부재를 설명하며 현재 자료를 이용해 과거 기록을 만들어 넣지 않는다.
- SNAPSHOT_INVALID: 저장 기록의 구조나 식별 연결을 확인할 수 없다. HTTP200/available=false/snapshot=null이며 내부 예외·원문 request를 노출하지 않는다.
- Job 없음은 기존 JOB_NOT_FOUND 오류와 HTTP404다. API 인증 middleware를 그대로 따른다.

URI·파일 경로·자격정보·허용하지 않은 원문 필드는 반환하지 않는다. snapshot 안의 ready_for_execution·scientific_approval·authorization_verified도 false로 제한한다. 이 형식·연결 검사는 데이터베이스 기록에 대한 서명 감사나 과학 검증을 뜻하지 않는다.

## 시각과 부작용

검사 시각은 **제출 시점**이다. 파일 삭제/변경 후에도 당시 기록을 조회할 수 있으며 현재 파일이 정상이라고 인증하는 기능이 아니다. Registry 해석·자산 해시 재검사·Job/Result/Trace 생성·카탈로그 쓰기를 하지 않는다. Workflow plan의 매 요청 현재 파일 재검사와 다르다.

## UI 인계

AgentCenter의 Job 조회에서 status와 companion을 구분해 표시한다. 입력 Job ID 변경이나 늦게 도착한 다른 요청 때문에 이전 진단을 현재 Job에 붙이지 않는다. snapshot 부재/손상/조회 오류는 통과가 아니며 기존 READY 실행 gate는 유지한다. [UI 구현·검증](32_job_snapshot_ui.md)을 따른다.

## 검증과 한계

관련12 PASS/6.726초, `evidence/integration/job-snapshot-tests-20261017.log`. 독립 검토에서 발견한 snapshot 자체의 상태·품질/권한 blocker 모순2종을 거부하도록 보완했고, 원래 코어가 만드는 정상/누락/동적/충돌/품질/권한 차단 기록은 읽을 수 있음을 확인했다. asset 삭제 후 당시 snapshot 조회, 중첩 민감 필드 제거, 신원 연결·형식 오류, legacy/404, 인증 상속, DB 불변·현재 Registry/파일 미검사를 검증했다.

전체 `scripts/test.ps1`은 **274건 중273 PASS/1 SKIP,70.655초·종료0**, `evidence/integration/job-snapshot-full-tests-20261017.log`. SKIP은 기존 실제 OS symlink 생성권한 시험이며 deterministic 경계 시험은 통과했다. UI adapter13 PASS·production build52modules/15.97초는 별도 로그다.

실제 UI5174→동일출처 개발 proxy→API8002(reload)에서 기존 legacy Job 상태/진단 부재, ID 변경 즉시 이전 기록 제거, 없는 Job404를 확인했다. `evidence/integration/job-snapshot-live-ui-20261017.json`과 문서32를 따른다. 기록이 있는 성공 snapshot 조회는 임시 fixture 시험이며이를 live 실자료 성공으로 확대하지 않는다. 실제 카탈로그·원장·manifest 전후 SHA가 같고 신규 과학 Job/Result/Trace는 만들지 않았다. 기관별 ACL·서명 감사·실행 시점 재검증·실제 executor는 별도 범위다.


## 실행 입력 바인딩 대조와 legacy 경계

[문서77](77_execution_input_binding.md)은 제출·전달 양쪽의 ordered 선택 메타데이터를 대조하는 미연결 순수 계약이다. 이 저장 snapshot 읽기 기능을 대체하거나 기존 Job에 manifest pin을 소급 기록하지 않는다. 실제 카탈로그의 legacy Job2건은 input_resolution/manifest pin이 없으며, 저장 request의 선택 선언으로 만든 로컬 replay는 UNKNOWN으로 남았다. supplied에 임의 manifest pin을 추가해도 과거 미기록은 채워지지 않는다. 이 replay는 실제 executor 전달을 관측한 증거가 아니며, request의 URI/AOI/model/params 전체를 검사한 결과도 아니다. 새 제출 시 신뢰 expected를 저장·연결하는 통합은 후속 PLANNED다.


## 별도 제출 binding capture의 저장

[문서78](78_submission_binding_capture.md)에새Job만의execution_input_binding_capture저장연결을추가했다. 이input_resolution읽기projection과HTTP계약은변경하지않았고과거Job/동일멱등replay는capture를재조회하거나역채우지않는다. 새capture의safe읽기projection/API·수동UI표시는후속PLANNED다. 현재API에서저장capture원문이나manifestpin을추가노출하지않는다.
