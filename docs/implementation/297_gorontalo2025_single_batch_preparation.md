# 297 — 새 고론2025 단일 batch 수집 준비

상태: **PREPARED_UNAPPROVED / COLLECTOR_NOT_EXECUTED**.291 실제 로컬계획 완료 핀을 받은 뒤 첫 고론2025 후보 한 곳만 선택했다. 원격/collector/원장·운영 source 쓰기/모델/실QA0이다. Root만 독립검토와 새 승인 뒤 실행한다. 고론2022는 대상에서 제외한다.

## 고정 입력과 선택

| 역할 | 준비 값 |
|---|---|
| source snapshot | `data/centers291-fresh-20261018/source.json` / SHA `9d491e6ede51cf29407add25b83919cc5d4150576a694c5019814b973d20c2b7` |
| proposal | 같은 디렉터리 `proposal.json` / SHA `e92d2cb2feefab44b1ed5209d56d3da02f0097306dd23bed0d2dbd0eca1a8a57` |
| prior64 | 같은 디렉터리 `prior-merged.json` / 직접 metadata SHA `278d02829ff3ffeef46532a7c41177c698a8ae060439060a87eabc2635ad0720` |
| active ledger 선언 | `4a4f4a47b522b9497b944ac00b29d2368a977c1a4eb6dfe972a34959fcc68722` |
| 선택 | `centers182-gorontalo-836ae25bed8a` / 2025 / train |
| 중심 lon/lat | 122.52546451445777 / 0.7527100768741187 |
| 한도 | 최대1 batch / nominal16patch / 65MiB 기존 공유 예산 예약 |

운영 source/ledger나68MiB snapshot 본문은 준비 단계에서 읽지 않았다. 완료된291 proposal/prior 메타데이터와 Root 제공 핀을 소비했다. 291 CLI를 다시 실행하지 않았다. 선택 proposal의 class_presence/actual_quality/execution은 모두false이며 계획창이 실제 취득에 적합하다는 승인이 아니다.

요청은 `evidence/integration/deficit297-prepared-request-root-20261018.json`에 새로 썼다. schema2, `GUARDED_DEFICIT_1024_REQUEST`, `candidate_metadata_policy=DEFICIT_AOI_BBOX_CONTAINS_V1`, maximum_batches1과 selected1을 명시한다. request canonical SHA는 **`e9ebe6f7dcbb986a853ed1749e97c4feafcacde1702c1937c946d7f6e2602487`**다. raw파일 SHA `abca225f439aa6adcceac5fdd126824e080c8490d188742c1463f31006c5b629`와 구분한다.

예상 새 key는 `center1024-gorontalo-2025-e9ebe6f7dcbb-73cbb072`다. 기존 key를 재사용/예약했다고 주장하지 않는다. Root 실제 실행 시 원장에 이 key가 없고 기존 pending2 전액이 같아야 한다.

## expected config의 독립 파생

기존279 요청은 형식 참고만 했고 새 proposal/source/prior/ledger/selected를 다시 결속했다. 과거279 승인·config SHA·selection context를 재사용하지 않는다. 현재 guard의391–406 파생 규칙을 직접 읽고 base config SHA `8b0c1b2aad13a3344200998ec62a18853c5308adf4ec57b1af835333845fd7e3`에서 `aois[].id=='gorontalo'` 단일 행을 선택했다. `province_id`만으로 찾는 이전 준비 오류를 반복하지 않는다.

이 base AOI의 id/province/bbox를 새 후보로 바꾸고2025/train·sixbands(blue/green/red/nir/swir16/swir22)·1024·64MiBCOG·prior0·search20/SCL5·cloud60·최종.8/예비.65·label_first·metadata검증·crop보존·재시도0·기존 collection policy를 파생한다. exact marker도 config에 포함한 뒤 guard와 같은 `sha256(json.dumps(config, sort_keys=True).encode())`로 계산했다.

독립 expected config SHA는 **`9d3618a258fbfd272c227cde90bffd3fc98fac2fd574864a69349a5825e41f71`**다. 검토용 새 config 문서는 `deficit297-expected-config-20261018.json`이며 파일 SHA와 config semantic SHA는 별도다. `.load_config()`가 추가하는 periods를 미리 섞어 digest를 바꾸지 않는다.

metadata binding은 정확 policy·새 canonical request SHA·source snapshot SHA의 세 값이다. 실제 worker의 selection_context는 collector가 fresh source/원장 가드를 통과한 뒤 만든다. 이 준비 파일은 그 실행 context나 실제 scene/window/support proof를 대신하지 않는다.

## supervisor 원판과 새 승인 경계

검증된285 supervisor 원SHA `66fe2ed5b76ed53342ce7cb84617cc500a3bb54c03ece64e65b65249fdee80ed`를 확인하고 `deficit297-before285-supervisor-20261018.py`에 원바이트 archive했다. 새 `deficit297-supervisor-root-20261018.py`는285 기반에서 새297 경로·고론2025·새 승인 status·완료285 긍정 native감사 조건·현재 UI context 사전핀만 변경했다. 최소 diff를 별도 `.patch`로 보존했다. 옛 PID/launch/request/approval는 재사용하지 않는다.

새 wrapper는 `deficit297-reviewed-code-pins-root-20261018.json`의 **`ROOT_APPROVED_ONE_GORO2025_V2_BATCH_AFTER_AUDITED285_AND_POST290`** status를 요구한다. 지금 만든 `deficit297-prepared-review-20261018.json`은 `PREPARED_NOT_ROOT_APPROVED_NO_EXECUTION`이며 실행 승인 파일이 아니다. Root가 독립검토·현재 핀/OS/lock·예산/공간 조건을 확인해 새 reviewed approval를 작성하기 전 collector를 실행하지 않는다.

직전285 감사 SHA `194affdac6f8838875251bdb8c6cb2807cc3492015b3b655ba71ae040ba8c455`와 완료/native16·eligible12·old rows/history/pending 보존·metadata two reads stable 조건을 요구한다.271 검증/현재 source code pins도 사전 검사한다. 이전 zero279 감사의 상태를 이번 긍정285 결과에 억지로 적용하지 않는다.

## source profile과 실제 수집 계약의 구분

완료294 선택 evidence가 전한 현재 API source profile config SHA는 `a644b5b2cdf8917d13028f7a89ceeb4996d5ad5dc54af2b6fb2c9fda2c98f9de`다. 현재 게시 pointer는 `996a88de2034e9803381d7ae4e906a0d1f418075675d13ef796fb5648bb472c0`다. 준비 단계에서 active config/pointer를 열지 않았다.

collector/deficit guard의 직접 입력은 strict request·base collection config·active source/원장 및 fresh inventory다. API의 `source-profile237-root-20261018.json`은 job config 파생 입력이 아니므로 a644 재결속 자체가 expected config SHA를 바꾸지 않는다. 모듈 `collection_source_profile.py`의 code pin과 이 JSON 내용 pin은 다른 역할이다.

이번 wrapper에서는 Root 실행 직전에 published_candidate_ref와 source_profile_config_ref를 별도 exact SHA로 확인하도록 추가했다. 이 UI context 핀을 새 원장/실영상 검증으로 사용하지 않는다. 수집 후 source가 변하면 profile/pointer가 다시 stale일 수 있으며 후속 감사/QA/게시/API를 별도로 진행해야 한다.

## 유지하는 보호와 검증 범위

기존 supervisor의 중복 Python collector/QA 및 execution lock 확인, fresh200 global lock 안 proof, 공유원장 4GiB·최대2worker/전역2초/첫429·물리3000/16×inflight, COG64MiB+metadata1MiB, 예산/미계측 pending 전액, oldpending2의136314880B exact 보존을 유지한다. pending을 환불/재정산하지 않는다. scene/window/support/split 및 최종80/주내95%/나지256 등은 기존 가드로 검증하며 완화하지 않는다.

wrapper는 reserved 가능성이 있는 자식을 launch journal/stdout 실패 때문에 버리지 않고 finally에서 wait한다. 실제 worker 종료와 정산·원본게시·잠금 해제는 별도 실제 근거/감사를 요구한다. 시작/exit0만으로 확보 성공을 보고하지 않는다. API/browser·학습·registry를 호출하지 않는다.

검증은 코드 읽기·메타데이터 SHA/선택·config 파생·메모리 compile뿐이다. supervisor를 import/실행하거나 fresh inventory·HTTP·collector·실QA를 실행하지 않았다. shared product를 변경하지 않았다. 준비 freeze/최소diff/request canonical/config SHA를 Root와 독립 검토 담당에 인계한 뒤 Root만 최종 실행을 결정한다. 현재 UI 기능 변경은 없고, 실제 새 자료가 생기면 원본/후보/게시 범위와 나지 기여를 분리해 UI·이해 담당에 인계해야 한다.


## 2026-10-18 21:58 KST — Root 실제 시작 인계

현재 실행 상태는 **STARTED_FRESH_PREFLIGHT / RESULT_UNCONFIRMED**다. 앞의 준비 절은 당시 실행0의 역사다. 추가 전에 원준비 문서 bytes를 `evidence/integration/deficit297-preparation-doc-original-20261018.md`에 보존하고 SHA `3eba37dd89bf908cc51bfa451af3876231ab99972fc3e7bf848d46acb0a81688`와 정확히 대조했다. 원준비 freeze의 문서 핀은 이 archive가 보존하는 판본이다. 기존 freeze나 코드 지문을 재발급/변경하지 않았다.

Root가 독립298의 추가차단없음 검토와 현재41핀을 확인하고 승인 SHA `ebf4d0b904a567275218736e14350ac086d74f69ba04fcb8ecb45a3681b221f6`로 직접 실행했다. Root 인계 시작은21:58:15.020913 KST, execsession12818, supervisor41744(parent28408), collector14628이다. 문서 담당은 OS·원장·launch·stdout을 추가 조회하지 않고 Root가 확인한 사실만 기록한다.

Root의 시작 관측은 launch record/실프로세스와 execution lock 존재, stdout0/terminal없음이다. **fresh preflight 시작만 확인됐고 worker 진입·실HTTP 계측·patch/적격/나지 확보·정산·완료는 모두 미확정**이다. 시작전 등록1747/적격1376/부족11·잔여1,845,284,187B 및 source9d491…c2b7/ledger4a4f…8722는 시작전 역사값이다. 이를 현재 원장값이나 수집 후 성과로 승계하지 않는다. 기존 pending 전액 보존 조건은 계속 요구한다.

Root만 collector/원장/lock을 소유한다. 실제 종료·정산·프로세스/잠금 해제 관측과 신규 최대16개의 bounded native 준비는 ml_pipeline299 담당이며 별도 Root GO 전 native0이다. 이 문서 담당은 추가 collector·QA·native·다른 감사·운영쓰기/원본읽기를 수행하지 않는다. 종료 실제 근거를 받으면 확인된 사실만 후속 기록한다. 현재 API/UI 최신 수량 반영·품질·학습 승인을 새로 주장하지 않는다.


## Root 실제 종료·native 완료 후속

현재 상태는 **VERIFIED_REAL_COMPLETED_NATIVE_INCREMENT / NEW_COHORT_QA_NOT_RUN**이다. STARTED 절은 당시 미확정 상태의 역사다. 추가 전 STARTED 문서 원바이트를 `evidence/integration/deficit297-started-doc-original-20261018.md`에 보존하고 SHA `51fde89eee4b988959f7e870a0155ebbb3b0abd4d4dac25ade9fec51da2c8e93`와 대조했다. 원준비 archive·코드·기존 freeze는 변경하지 않았다.

Root가 지정299 담당의 단일 bounded native 완료 근거 SHA `e8c51e5c0afd86d4f0d89a58121103bad76ff3a5e4504079c41217ac08731096`와 함께 인계한 실제 결과는 **신규16개/적격15개/나지0**이다. 이 문서 담당은 추가 감사·배열/원본/원장 읽기·HTTP·collector·QA를 수행하지 않고 Root 완료 인계를 기록했다.

완료 후 원본은 등록1763/적격1391(train849/val292/test250), 고론2025 적격33으로 최소28 충족이며 남은 최소수량 부족은 동자바2025 한 셀이다. source SHA는 `9e63564c87647a144665bbb6bbe49b4a95d09bbd2c3bc0f3725861c54d5e7109`/68,887,373B, ledger는 `574d382dd9da51ae56dc8fb135532f8f2e5c542b2c4cafdf73a6ee8dd9c6045f`다. Root 잔여 예산1,822,603,826B·oldpending2 전액136,314,880B 보존을 인계했다. 이전 시작전 숫자를 현재값으로 재사용하지 않는다.

15개는 **native로 검증한 원본 적격 증가**이며 새 cohort QA/게시 승인15개가 아니다. 현재 게시1360은 old9d 기준이어서 새9e와 stale 상태를 정직하게 유지한다. 나지0이므로 나지 gate나 학습을 해제하지 않는다. 실행/terminal의 종료시각·elapsed·상세정산액은 이번 Root 인계에 없으므로 추정해 추가하지 않는다.

후속302는 기존68개를 제외하고 동자바2025만 겨냥하는 로컬계획 준비이며 Root별도GO 전 실제CLI/source복사0이다. Root는 남은 동자바 소단위 이후 최종 원본을 고정해 QA를 단1회 묶는 전략을 인계했다. Root301의 새current9e profile/API는 별도 담당이며, 이 문서로 API/브라우저 current 반영까지 완료했다고 주장하지 않는다. 최종 문서 지문을 Root에 전달해 이해자료에서 원본1391/native증가15와 게시1360/나지0을 구분하도록 인계한다.
