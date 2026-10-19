# 297 고론탈로2025 수집 준비판 독립 정적 검토

## 결론과 검토 범위

상태는 **IMPLEMENTED_UNVERIFIED — 최종 동결 준비판 정적 검토**다. 최종 freeze 통지 뒤만297 코드를 읽고285 원판·현재 guard와 대조했으며 추가 실행 차단 결함을 발견하지 못했다. 실행 승인이나 실제 수집·품질·정산 완료 판정은 아니다. 운영 source/ledger/profile/pointer·래스터·부분 QA 산출물 읽기, HTTP·collector·새 시험·실QA 실행은0이다. 완료290 QA 및285 native 감사를 반복하지 않았다. 제품 코드 수정0이며 이 문서만 새로 작성했다.

최종 evidence/integration/deficit297-preparation-freeze-20261018.json SHA는57dda7cae3e55ce489930eb0eae69bd2ca16b3c9e2344c1bc5d49f368683b8ad다. 그7개 파일의 byte/SHA를 모두 확인했다. supervisor SHA1b41991db71ce006f7ef46ed5fc67cb5e7ad92d79a4b484b30e50bef4993bfaa, prepared-review SHA24c6dffb3969de196590e12b7467c914c8fe1bd0ab939a9d211480eb853498b3, 최소diff SHA060239354636e54fb487f429836cc71fe69ed96ed4c5203578dca513080139f2다.285 원판 archive SHA66fe2ed5b76ed53342ce7cb84617cc500a3bb54c03ece64e65b65249fdee80ed와 원판이 유지된다.

## 요청·계획·config 결속

새 prepared request 파일 SHAabca225f439aa6adcceac5fdd126824e080c8490d188742c1463f31006c5b629와 canonical SHAe9ebe6f7dcbb986a853ed1749e97c4feafcacde1702c1937c946d7f6e2602487을 구분하고 후자를 직접 계산해 일치 확인했다. schema2와 정확한 DEFICIT_AOI_BBOX_CONTAINS_V1,1batch/선택1개,고론탈로2025/train/1024를 고정한다. 선택은 centers182-gorontalo-836ae25bed8a,예상key는 center1024-gorontalo-2025-e9ebe6f7dcbb-73cbb072다.

요청은291의 새 proposal e92d2cb2feefab44b1ed5209d56d3da02f0097306dd23bed0d2dbd0eca1a8a57, 고정 source사본9d491e6ede51cf29407add25b83919cc5d4150576a694c5019814b973d20c2b7, prior-merged278d02829ff3ffeef46532a7c41177c698a8ae060439060a87eabc2635ad0720 및 기존 경계/base config를 참조한다.291 완료 evidence에는 prior64 보존·새 제안4·원본원장 핀 안정·117header·원격0이 기록돼 있고297 준비 문서/요청과 모순이 없다. 담당자는 실제 운영/계획 source 본문이나 prior64 배열을 다시 읽지 않았으며 증거와 참조 계약의 대조만 수행했다. Root는 실행 전에 참조 파일의 실제 SHA를 다시 검사해야 한다.

wrapper는 핀 고정 base config의 aois[].id=='gorontalo' 정확히1개를 골라 새 id/province_id/bbox를 파생한다. 현재 guard391–406과 동일하게2025·6밴드·1024·COG64MiB·prior0·search20/SCL5·sort/cloud60·최종 유효.8/예비.65·label_first·metadata 검증·crop 보존·retry0을 설정하고 exact v2 marker를 config에 넣은 다음 SHA를 계산한다. expected config 문서의 semantic SHA를 직접 계산해9d3618a258fbfd272c227cde90bffd3fc98fac2fd574864a69349a5825e41f71과 맞음을 확인했다. 파일 raw SHA4d2c6b83dfce69b66e929fbbae24bd4e4f7bd3a6bc4ad4240970c2a51370c385와 다르다. 이 계산은 예상 config 계약이며 fresh source/support/scene/COG 기하 검사의 실행을 대체하지 않는다.

## 285 대비 변경과 종료 책임

전체 최소diff는297 경로/새승인 상태·연도2022→2025·직전 감사 참조 및 게시/profile 사전핀 추가로 한정된다. launch_and_wait 함수는285와 AST가 완전히 같다. launch 기록/알림 출력이 실패해도 이미 시작한 자식의 wait가 finally에서 수행된다. 과거의 검증 코드를 읽은 것이며 새 자식 시험을 수행한 것은 아니다.

직전285 SHA194affdac6f8838875251bdb8c6cb2807cc3492015b3b655ba71ae040ba8c455에 결속하고 COMPLETED_BOUNDED_NATIVE_AND_TRACE_CHECKED,실native16/적격12,old rows/history/pending 보존,metadata 두읽기 안정 조건을 요구한다.279의0패치 상태를 잘못 재사용하지 않는다. 현재 published1360 pointer996a88de2034e9803381d7ae4e906a0d1f418075675d13ef796fb5648bb472c0와 source-profile configa644b5b2cdf8917d13028f7a89ceeb4996d5ad5dc54af2b6fb2c9fda2c98f9de는 approval의 별도 참조 SHA로 시작 전에 확인한다. 이 두 context 핀은 collector job config나 학습 승인 입력이 아니며 고정 base config와 구별한다.

prepared-review는 PREPARED_NOT_ROOT_APPROVED_NO_EXECUTION이다. 실제로 필요한 status는 ROOT_APPROVED_ONE_GORO2025_V2_BATCH_AFTER_AUDITED285_AND_POST290이며 Root가 새 승인 파일을 별도로 만들어야 한다.40개 source_pins 및 runtime 검증을 확인하는 구조이지만 wrapper 자체가 핀 목록40개의 완전성을 고정 집합으로 강제하지는 않으므로 Root가 최종 목록을 검토해야 한다. 준비파일을 승인파일로 간주하거나 과거 request/approval/PID를 재사용하지 않는다.

## 유지된 보호와 후속 실행 조건

현재 source9d491…c2b7·ledger4a4f…8722는 approval과 요청 참조로 확인하며, 원pending2행은235 원형과 정확히 같고 예약합136,314,880바이트여야 한다. 추가예산4GiB·rate limit 비활성·65MiB 이상 예약 여유·새 key 미등록을 검사한다. 자식 직전 원본·원장 원바이트도 다시 비교한다. 시작 전 잔여1,845,284,187바이트는 Root 인계 기준값이며 미래 성과·최종 정산량으로 더하지 않는다. 원pending은 이미 사용액에 포함돼 재차감하지 않는다.

OS/lock 부재 사전검사는 비원자 관측이다. 실제 core는 O_CREAT|O_EXCL 전역 lock을 얻은 뒤 validate_request로 fresh 전체 보호를 검사하고, 그 뒤 예약한다.2worker 제한·공유2초 간격·첫429 공유 중단·물리3000·COG64MiB+metadata1MiB·중앙 정산/발행/실측 보존은 기존 코드 그대로다. core가1batch 최대16을 검사하며 wrapper의 예상 config만으로 보호가 통과했다고 말하지 않는다. 원본 분할·모델·profile/게시파일을 collector가 임의 바꾸는 권한은 새로 생기지 않는다.

Root는 실제 source/ledger/pending·40코드핀·정확 request/config canonical·OS/lock을 최종 확인한 후 단일 collector를 실행해야 한다. 실행 뒤 terminal·worker·실정산·lock/OS 종료를 분리 관측하고, 신규가 있으면 Root 원본 고정·별도 GO 뒤 해당 신규 최대16만 단일 bounded native 감사한다.0패치면 native0의 좁은 종료/정산/보존/실탈락 사유 감사만 수행한다. 수집 후 source가 달라지면 기존 후보/profile의 stale 상태와 후속 QA·게시·API/UI 반영을 다시 구별한다. 학습 준비false·나지 부족·독립 정확도 미검증과 전체 미완료는 그대로다. 내부 준비 리뷰 자체는 UI 동작을 바꾸지 않으며 실제 완료 뒤 Root의 이해자료·web_ui 인계를 따른다.
