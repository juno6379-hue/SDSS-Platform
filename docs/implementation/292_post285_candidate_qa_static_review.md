# 290 고정 후보 QA 준비판 독립 정적 검토

## 결론과 상태

상태는 **IMPLEMENTED_UNVERIFIED — 동결 준비 코드의 독립 정적 검토**다. 최종 동결판에서 추가 실행 차단 결함은 발견하지 못했다. 실제 QA·학습·게시·API/UI 성공을 확인하거나 실행을 승인한 결론은 아니다. 담당자는 코드와 준비/동결 증거만 읽었고 운영 source·ledger·policy·pointer·래스터 조회, HTTP, 제품 시험·QA 실행은0이다. 285의 완료 native 감사도 반복하지 않았다.

최종 freeze를 전달받은 뒤 다음 지문을 확인했다. 변경 중 파일을 최종 근거로 사용하지 않았다.

| 파일 | SHA256 |
|---|---|
| priority290-preparation-freeze-20261018.json | d98983f31085ff1f65435a5b9357b35dd98b12cf4a7a1e6bfd3afd7044268232 |
| priority290-preparation-20261018.json | e9260f8ee5c81a63a9a8221e24b439f5e7c0b2b5e5955129be6b0cf169ace4ef |
| priority290-runner-20261018.py | 68b271471887eca7259dd72196a1515ecef57a50239f25ba917ea194c3877c3e |
| priority290-runner-vs273-20261018.diff | b4b964ae1057a4f3ee37d67ceb2e56a77553e369433793b70cff30ebc97ea89b |
| 290_post285_candidate_qa_preparation.md | fb5726916211a77edb54e5ac447e24b583d2ac0f22d8be9953835c3c9052bd0b |

위 evidence 파일은 evidence/integration 아래, 문서는 docs/implementation 아래다. freeze의4개 산출물 byte/SHA가 전부 맞았다. 준비판의16개 제품 코드핀은273과 정확히 같으며 실제 코드파일 byte/SHA도 모두 일치했다. 이는 소스 지문 대조이며 새 제품 시험16개를 실행했다는 뜻이 아니다.

## 273과의 차이와 단일 실행 경계

runner 전체를 읽고273 최종판과 diff를 대조했다. 변경은290 ID·고정 준비 SHA·승인 kind와 경로, protected_expected 대조1줄뿐이다. 기존 prepare_priority_candidate164.main을 직접 부르는 callsite는 정확히1개다. subprocess로 QA를 다시 시작하거나 실패를 재실행하는 경로가 없다. 새 work/evidence/log/launch/terminal 경로가 이미 있으면 시작을 거부하고 exclusive 출력으로 부분 실패를 보존한다. 자동 상한 증가·자동 재시도·후보 게시·모델 훈련은 허용하지 않는다.

runner는 고정 준비 JSON의 byte SHA를 두 번 확인하고16개 코드핀을 검사한 뒤 같은 backend.app.ml.manifest_resource_profile 모듈의 scope를 연다. descriptor 전체와 digest를 고정 준비값에 대조하며 기존 active scope가 없음을 요구한다. source 상한은 정확히134,217,728바이트(128MiB), source/history 관련 행3000·depth32·node4,000,000·누적 JSON 입출력17,179,869,184바이트(16GiB)다. ContextVar scope 안에서 CLI를 정확히 한 번 부르고 동일 budget 객체가 유지되는지 검사한다. 준비 JSON bootstrap의 두 실제 읽기는 같은 budget에 charge한다. 로그도4MiB 및 같은 누적 예산으로 계측한다. 이 profile은 JSON 입출력 한계이며 프로세스 RSS16GiB 제한이나 전체 래스터 입출력 상한을 뜻하지 않는다.

## 고정 입력과 승인 계약

준비 source는285 후속 원본 SHA9d491e6ede51cf29407add25b83919cc5d4150576a694c5019814b973d20c2b7·68,220,381바이트·보고 등록1747행이다. policy는01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7, 직전285 native 감사는194affdac6f8838875251bdb8c6cb2807cc3492015b3b655ba71ae040ba8c455에 결속한다. source/policy 내용과 실제 행수·분할·새 후보 수는 실행 후 기존164 제품이 검사할 책임이며 준비판의 예상값을 실제 QA 결과로 확정하지 않는다.

Root GO는 절대 evidence 경로의 JSON으로 받아야 한다. kind=PINNED_CANDIDATE_QA_290_GO, approved=true, run_id, preparation/native/source SHA와 source bytes, profile MARKER, no_active_collector=true, execution_lock_absent=true의 정확한 키 집합과 값을 요구한다. 승인/collector부재/lock부재의 bool은 정확히 True인지 추가 확인한다. MARKER는16개 코드핀에 포함된 실제 profile 모듈에서 가져오며 임의 범위 서술로 대체하지 않는다. 이는 고정 hash/marker 계약이지 암호학적 사용자 서명이나 외부 운영 승인 검증은 아니다.

실행 전 lock 부재와 source byte 크기를 검사하고 CLI에 source/policy 기대 SHA를 전달한다. 실제 source SHA의 직접 검사는 기존164가 출력 전 및 각 QA 뒤에 수행한다. ledger는 준비 provenance이며 QA 입력이 아니고 이 runner의 QA 결과가 원장 전체 재감사를 대신하지 않는다. Root는 별도로 source/ledger hold와 실제 OS/collector 상태를 유지해야 한다. runner의 no_active_collector는 GO 선언이며 자체 OS 프로세스 감시나 수집기 O_EXCL 잠금과 동등하지 않다.

## 산출물·보존·실패 처리

성공 후 summary의 완료 상태·profile marker·source SHA·file_sha_mismatches=0·training_executed=false를 확인한다. candidate-package/receipt.json, stage/staging-receipt.json, qa/qa-receipt.json의3개 receipt가 schema_version2와 동일 profile MARKER를 갖는지 검사한다. 이 준비 runner의 확인만으로 receipt 전체 출처·정확 retained partition·최종 pointer 승계가 승인되는 것은 아니며 제품 CLI와 후속 독립 검산·게시 계약의 책임을 유지한다.

기존1348 latest-candidate pointer와 candidate-receipt275 두 파일은 시작 시 정확한 기대 SHA1aee2e01583a024c508d6fdac0d3c4fac2260bbd449ea12269d5e033c1dcc7b4와 맞아야 한다. 새로 추가된 protected_expected 검사는 시작 전에 이미 다른 pointer로 바뀐 경우도 차단한다. 실행 뒤 같은 두 파일을 재검산하고16개 제품 코드핀도 다시 확인한다. 이 보호는 두 파일과 해당 코드의 관측이며 모델/원장/다른 모든 파일을 해시한 전역 불변성 검사라고 표현하지 않는다.

CLI 또는 후검사 예외는 부분 출력 보존·재시도 금지 상태로 종료한다. 일부 후검사/terminal 쓰기 자체가 실패하면 일반 wrapper 미완료 stderr만 남을 수 있으므로 terminal 부재를 성공이나 자동 재실행 허용으로 해석하지 않는다. 동일 실행 중 새 collector를 시작하지 않는 Root 운영 배타성이 필요하다. 후속 실제 QA 완료와 후보 수·나지 차단은 실행 증거를 받아 별도로 보고하며, 이 정적 내부 작업 자체는 UI 제품 동작을 바꾸지 않는다. Root의 완료 후 이해자료·API/UI 인계를 계속 유지한다.
