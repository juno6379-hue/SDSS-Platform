# 309 최종 고정 후보 QA 준비 독립 정적 검토

상태는 **IMPLEMENTED_UNVERIFIED — 최종 동결 준비 코드 정적 검토**다. 추가 실행 차단 결함은 발견하지 못했다.309 최종freeze 통지 뒤만 읽었으며 운영 source·ledger·policy·pointer·부분 QA 결과·래스터는 읽지 않았다.실QA·native·HTTP·collector·새 시험·제품코드 편집은0이다. 실제 QA 승인과 실행은 Root/ML 담당의 별도 작업이다.304 native GO를309 QA GO로 간주하지 않는다.

freeze evidence/integration/priority309-preparation-freeze-20261018.json SHAe73b65af5ed2acd84877f38c09e0d66da2a0002346356e2f45c681d5ac3a39fe의6개 파일 byte/SHA를 모두 확인했다. runner922e70584c51ac0c9cd247bc22d49be4bdf9936c8fcdb3b800be5b5874ea4e83,preparation698bb2a02155de2027d138d65820e836767f6475003f57301cc0f1a5de73fd33,diff1329d3eb2379910edfde1f9a5dd7d698b6837e522a243fa64ab5c9150c7ab5a7,doc30914d6930a8621172002bff0761e7690553303ca32346fead61aba2e67858d2b72가 일치했다.290 원판 사본2개도 이전 지문 그대로다. 준비판의16개 코드핀은290과 정확히 같고 실제 제품 코드 byte/SHA도 모두 일치했다. 이는 지문 대조이며 새로운 제품 시험을 실행한 결과가 아니다.

runner 전체는290의 ID를309로 바꾸고 준비SHA를 새값으로 치환한 문자열과 정확히 같다. 단1 cli_main callsite를 확인했다. 기존 검증 제품164 CLI를 같은 프로세스에서 정확히 한 번 부르고 재시도·상한 증가·게시·훈련 경로를 추가하지 않았다. 새 run_id는 guarded309-20261018이며 work/evidence/log/launch/terminal의 별도 경로가 없어야 시작한다. 부분 산출물은 exclusive 생성·보존한다.

준비 source는0c149628ccfa916ee976e561c5da05f9ccc810cbeab7d233a05b9bc7eff54658·69,564,847바이트·보고1779행이다. 기본64MiB 초과2,455,983바이트지만 명시128MiB 안이며 자동 상향하지 않는다. policy01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7와304 native7e933d923f6a7507a878f66bd7fea391b7b181779746f175567f0febdf8c884c에 결속한다. 원본 적격865/292/250은 준비판의 보고값이며 이 검토가 다시 센 값이나 최종 후보 수가 아니다. ledgerd5ee31ff7970adaaa6b166805c240616efa8e9af713bb8394c7a166346f21c91는 준비 provenance이고 QA 입력이 아니다.

scope는 기존 bounded128m-3000-v1 descriptor 전체와 digest를 대조하고 ContextVar가 비어 있을 때 시작한다. source/candidate128MiB·행3000·depth32·node4,000,000·누적 JSON 입출력16GiB를 같은 budget에 유지한다. bootstrap 준비 JSON의두 읽기도 charge하고 로그는4MiB 상한 및 같은 누적 입출력에 계상한다. 이 값은 RSS16GiB나 모든 래스터 입출력 제한을 뜻하지 않는다. CLI 이후 동일 budget 객체가 active인지 검사한다. source/policy 실제 SHA는164가 출력 전 및 각 QA 뒤에 검사하며,실제 source/history·후보 행수와 class/분할/누출은 기존 제품 QA의 책임이다.

GO는 절대 evidence 경로의 PINNED_CANDIDATE_QA_309_GO,정확한 키 집합·run_id·준비/native/source SHA·source bytes·실제 MARKER를 요구한다.approved/no_active_collector/execution_lock_absent는 정확히 True여야 한다. 실제 lock 부재도 검사하지만 OS 프로세스를 감시하거나 collector lock을 잡지는 않는다. Root는 실행 직전 실제 collector/QA 부재·source/ledger hold를 재확인해야 한다. 준비 단계 OS 부재 선언을 미래 실행까지 보장된 사실로 읽지 않는다. MARKER는 지문 계약이며 암호학적 기관 승인 서명으로 해석하지 않는다.

기존1360 pointer와candidate-receipt293은 시작 전 protected_expected996a88de2034e9803381d7ae4e906a0d1f418075675d13ef796fb5648bb472c0에 정확히 맞아야 한다. CLI 뒤 동일 두 파일과16개 코드핀을 다시 확인한다. 이 보호는 지정 파일 범위이며 원장·모델·모든 운영파일의 전역 재해시를 수행한 것으로 보고하지 않는다.

성공 summary는 완료상태·동일 profile marker·source SHA·file_sha_mismatches0·training_executed false를 요구한다. candidate-package/receipt.json,stage/staging-receipt.json,qa/qa-receipt.json의3개 receipt는 schema2와 같은 MARKER여야 한다.후속 retained partition·exact source rows·receipt 전체 결속·새 pointer 승계는 기존 제품과 Root 별도 게시 검산을 계속 요구한다. wrapper의 성공만으로 게시·UI·학습을 승인하지 않는다.

CLI/후검사 실패는 부분 보존·exit2·재시도 금지로 처리한다. 일부 후검사나 terminal 쓰기 자체가 실패하면 일반 wrapper 미완료 stderr만 남을 수 있어 terminal 부재를 성공이나 재시도 허가로 해석하지 않는다. 실제 후보 수는 아직null이다.304의 마지막 셀 최소량 충족과 나지 기준·최종 학습 준비는 별개이며 최종 QA 결과로 차단을 정직하게 유지해야 한다. 실제 완료 뒤 Root가 지문·후보/분할·품질·예산 보존·후속 게시/API/UI 및 이해자료를 각각 인계한다. 이 정적 내부 검토 자체는 UI 제품동작을 바꾸지 않는다.
