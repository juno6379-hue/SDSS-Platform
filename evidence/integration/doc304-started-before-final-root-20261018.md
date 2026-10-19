# 304 — 남은 동자바2025 단일 batch 수집 준비

상태: **PREPARED_UNAPPROVED / COLLECTOR_NOT_EXECUTED**.302 실제 로컬계획의 첫 동자바 후보 한 곳만 선택했다. shared product 변경·운영 source/ledger 쓰기/읽기·원격/collector·모델·실QA0이다. Root 독립검토·새 GO 전 실행하지 않는다.

## 새 요청과 독립 설정

선택은 `centers182-east_java-5141c64815b2`/2025/train, 중심112.12452853355475,-7.764251076494455다. 최대1 batch/nominal16patch다. 계획상 inside_fraction1·EastJava 적격27/부족1은 실제 취득/최종 품질 승인이 아니다.

| 입력 | 핀 |
|---|---|
| `data/centers302-fresh-20261018/proposal.json` | `e145e1fc2028bb00c26ceace8f814281fa8c48a9663ea18b1f31548d4eeec842` |
| 같은 디렉터리 `prior-merged.json` | `60b748a50f05d847bb1807fa18a763d44e88007c672eb805a52e255d5e5e74fa`/68개 |
| 같은 디렉터리 source.json ref | `9e63564c87647a144665bbb6bbe49b4a95d09bbd2c3bc0f3725861c54d5e7109` |
| active ledger 선언 | `574d382dd9da51ae56dc8fb135532f8f2e5c542b2c4cafdf73a6ee8dd9c6045f` |

준비에서는 완료302 proposal/prior 메타데이터와 code/config만 읽었다. source snapshot 본문/운영 원장은 열지 않았다.302 CLI를 다시 실행하지 않았다.

새 요청 `evidence/integration/deficit304-prepared-request-root-20261018.json`은 schema2/`GUARDED_DEFICIT_1024_REQUEST`/`DEFICIT_AOI_BBOX_CONTAINS_V1`/selected1/maximum_batches1이다. canonical SHA는 **`981abcd9b78b6eaa94dcb48a2f2bc62346ac939967076490b41c0c10e03f0987`**, rawfile SHA는 `b07fd377056542066029cf879b1c52261d61f6976e56bbf298a89298178b8c39`다.

current guard391–406과 같은 base config `8b0c1b2aad13a3344200998ec62a18853c5308adf4ec57b1af835333845fd7e3`에서 **AOI id=east_java** 한 행만 골라 새 id/province/bbox와2025/sixbands/1024/64MiB/prior0/search20/SCL5/cloud60/최종.8·예비.65/label-first·metadata검증·crop보존·재시도0/기존 collection policy를 독립 파생했다. metadata marker를 넣은 뒤 guard와 같은 JSON 해시 식으로 계산했다. `.load_config`가 추가하는 periods는 미리 섞지 않는다.

expected config semantic SHA는 **`31044c97e5dd1cf84648eec174975eacd9b5f8e1eacfcbf50e355bc0bb7d657a`**다. 새 검토용 `deficit304-expected-config-20261018.json`에 파생 내용을 보존했다. 옛 고론 config/승인/context를 재사용하지 않는다. 새 예상 key는 `center1024-east_java-2025-981abcd9b78b-9c40f177`이며 실제 예약했다고 주장하지 않는다.

metadata binding은 policy·새 canonical request SHA·9e source SHA다. 실제 selection_context/scene/window/support 가드는 Root 실행에서 fresh source/원장·inventory를 검증한 뒤 collector가 만든다. 준비 파일이 그 proof를 대신하지 않는다.

## supervisor 원판과 실행 승인

부모297 supervisor SHA `1b41991db71ce006f7ef46ed5fc67cb5e7ad92d79a4b484b30e50bef4993bfaa`를 확인하고 `deficit304-before297-supervisor-20261018.py`에 원바이트 보존했다. 새 wrapper는 `deficit304-supervisor-root-20261018.py` SHA `f8d74ec8597f111326db71e2f93ff09516dc3341a06c15cb9f7b30d7a45c26b1`다. 변경은 새304 경로/status·east_java·직전297 native16/15 조건뿐이며 최소 `.patch`를 기록했다.

실제 wrapper는 새 `deficit304-reviewed-code-pins-root-20261018.json`의 **`ROOT_APPROVED_ONE_EASTJAVA2025_V2_BATCH_AFTER_AUDITED297_AND_CURRENT301`** 승인을 요구한다. 현재 `deficit304-prepared-review-20261018.json`은 `PREPARED_NOT_ROOT_APPROVED_NO_EXECUTION`으로, Root 승인 파일이 아니다. Root만 현재 OS/lock/source·ledger/예산·새 key 부재·전체 코드 지문/독립리뷰를 확인해 reviewed approval를 작성하고 실행한다. 이전297 approval/PID/launch/request를 재사용하지 않는다.

직전297 native SHA `e8c51e5c0afd86d4f0d89a58121103bad76ff3a5e4504079c41217ac08731096`,완료/native16·eligible15·old rows/history/pending exact·metadata two reads stable를 요구한다. 이는 이전1747행 보존의 완료 근거이며 현재1763 원본의 fresh proof를 대신하지 않는다. 현재 원본1763/적격1391과 새 cohort QA는 구분한다.

## UI profile 맥락과 유지하는 보호

현재 API source profile ref는 `source-profile237-root-20261018.json` SHA `b9a2cd5cfe20bb570281882adcd1f47b4b81b0be4e69c0f0b91d606f0cd17f9e`,게시 pointer SHA는 `996a88de2034e9803381d7ae4e906a0d1f418075675d13ef796fb5648bb472c0`다. 준비 중 active 두 파일은 읽지 않았다. Root 실행 전에 wrapper가 별도 exact refs를 검사한다. profile JSON은 API 맥락이며 base collection config/새 expected config 입력이 아니다. old1360 pointer가 old9d로 stale인 상태를 숨기거나 current9e proof로 사용하지 않는다.

기존4GiB/최대2worker·공유2초/첫429·물리3000와16×inflight·COG64MiB+metadata1MiB·global execution lock 안 fresh inventory·기존scene/window/support/split·80/95/나지256·원본모델 보호를 유지한다. oldpending2 전액136314880B를 원235 pending record와 exact 비교하며 임의 환불/정산하지 않는다. 미래 사용량/신규 적격은 추정하지 않는다.

자식 시작 뒤 launch journal/stdout 실패에도 finally wait해 예약 가능성이 있는 자식을 버리지 않는 기존 supervisor를 보존한다. 실제 종료/정산/잠금 해제·신규 최대16 bounded native·필요최종 QA/API/UI는 각각 실제 근거가 필요하다. 시작/exit0을 확보 성공으로 보고하지 않는다.

## 준비 검증과 후속

코드 read/metadata SHA·선택/메모리 compile, wrapper의 config 파생 fragment만 독립 실행해 prepared expected config와 exact 같음을 검증했다. collector import·fresh inventory/fullscan·OS조회·실자료검사·원격·수집·실QA는 수행하지 않았다. 신규 코드 변경은 supervisor 준비 파일에 한정했고 shared collector는 편집하지 않았다.

최종 freeze/요청·config SHA/최소diff를 Root와 독립리뷰 담당에 인계한다. 새 native 원본1391과 old게시1360을 혼용하지 않으며 나지0/학습false를 유지한다. UI 기능 변경이 없는 준비라 화면 수정은 필요 없다. 실제 취득 뒤 최종 고정 QA를 묶는 Root 전략과 API/브라우저/이해자료 후속은 별도 승인/증거로 진행한다.


## 2026-10-18 22:17 KST — Root 실제 시작 인계

현재 실행 상태는 **STARTED_FULL_PREFLIGHT / RESULT_UNCONFIRMED**다. 앞 준비 절의 실행0은 당시 역사다. 추가 전 원준비 bytes를 `evidence/integration/deficit304-preparation-doc-original-20261018.md`에 보존하고 SHA `b9e751453c9637c15a4351198e1103580dc3438d2e0afb91f1fc9ec136327f1d`와 대조했다. 기존 freeze의 문서 핀은 archive가 보존한 역사 판본이며 코드·기존 freeze를 바꾸거나 재발급하지 않았다.

Root는7개 freeze/현재42코드·source/ledger·pending 원배열·profile/pointer·독립 config를 검산하고306 독립리뷰 SHA `7a781af4e58b55ecefd164de0f98b741a9a621124ac84ce5fdf4d624f407ce9d`의 추가차단없음 결론 뒤 실제 승인 SHA `d5225e2149cdf99533b569b69961b15e57a1a334fca9b99bd4323efbca5fb751`/43source핀으로 직접 실행했다. Root 인계 launch22:17:46.597291 KST, execsession94106, collector33032, supervisor43984(parent6376)다.

Root 관측은 launch/실프로세스/lock 존재·stdout/stderr0·terminal없음이다. **full preflight 진입만 확정됐고 worker 진입·실HTTP·patch/적격/나지 확보·정산·완료는 미확정**이다. 실패나0patch일 가능성을 지우지 않고 실제 결과를 기다린다. 시작만으로 성공이나 임의 환불/정산을 기록하지 않는다.

원본1763/적격1391/부족1·잔여1,822,603,826B와 oldpending2 전액136,314,880B는 시작전 역사값이다. 실행 후 현재값으로 자동 승계하지 않는다. 새 원본/후보QA/API·UI 반영도 아직 주장하지 않는다.

단일 종료 관측과 신규 최대16 bounded native 준비는 ml_pipeline307 소유다. Root의 별도 최종 GO 전 native0이며 다른 감사·추가collector·QA를 중복 실행하지 않는다. 문서 담당은 운영 파일/OS/원장·결과를 조회하지 않고 Root 시작 인계만 추가했다. 실제 종료·감사 근거가 오면 확인된 사실만 후속 마감한다.
