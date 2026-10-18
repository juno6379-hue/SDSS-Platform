# 148 — 중단 수집 조사와 기존 예약을 보존한 다른 작업 계속

## 쉬운 설명

수집은 위성사진 한 장 전체를 받는 대신 필요한 작은 영역과 밴드를 읽고, 같은 해 토지피복 참조를 맞춰 학습용 패치로 나누는 작업이다. 여러 밴드를 모두 받아야 하나의 영상으로 조립할 수 있다. 현재 중단된 두 작업은 **반텐(Banten) 2023년의 새 공간창 1개와 서자바(West Java) 2023년의 새 공간창 1개**다. 이미 확보한 1,384개 패치 전체가 사라진 문제가 아니다.

두 작업은 일부 밴드만 받아놓은 상태로 끝났다. 반텐에는 B02/B03/B04/B08/B11 원본 crop이 있고 B12와 최종 조립 영상은 없다. 서자바에는 B02/B03/B04가 있고 나머지 밴드와 최종 조립 영상은 없다. 두 곳 모두 동년 Esri 참조와 STAC/교정 메타데이터 일부는 있다. 그러나 완료 보고서와 작업자 종료 보고서가 없고 완성한 cell도 기록되지 않았다. 따라서 부분 파일을 완성 패치처럼 더하거나 학습에 넣지 않는다.

예산 장부에는 작업을 시작하기 전에 최대 사용량을 예약한다. 갑자기 끝나면 실제로 얼마를 받았는지 확정할 수 없으므로 예약을 그대로 둔다. 이번 변경은 그 예약을 환불해 다시 쓰는 기능이 아니다. **두 미완료 작업의 예약과 파일은 보존하고, 남은 동일 예산 안에서 다른 미예약 작업부터 계속할 수 있게 하는 명시 옵션**이다.

## 실제 조사와 원인 판단

**VERIFIED_REAL:** 새 read-only 조사에서 보호한 52개 경로의 존재·크기·SHA·mtime이 전후 일치했다. 네트워크 요청과 원본 쓰기는 0이다. 두 config는 원장 SHA와 일치하고 실제 종료 파일은 모두 누락이다. `recovery`, `terminal`, `aggregate`, `snapshot` 증거는 아래 경로에 새 파일로 보존했다.

| 구분 | 반텐 2023 | 서자바 2023 |
|---|---:|---:|
| 정확한 batch key | `parallel-v2-extra-banten-2023-v2-laneB-banten-boundary-01` | `parallel-v2-extra-west_java-2023-v2-laneB-west_java-boundary-01` |
| 수집 시작 이벤트 KST | 10월 16일 16:59:33 | 10월 16일 17:00:45 |
| 마지막 window-state 수정 KST | 10월 16일 17:04:17 | 10월 16일 17:03:57 |
| 장부에 보존하는 전체 예약 | 68,157,440B | 68,157,440B |
| window COG 계상 상한 | 52,151,987B | 44,105,728B |
| window COG 실측 기록 | 18,597,555B | 10,551,296B |
| 상한−실측 | 33,554,432B | 33,554,432B |
| 완성 cell / 종료 보고서 | 0 / 없음 | 0 / 없음 |

상한−실측 32MiB는 마지막 COG fetch 전에 예약한 상한이 정산되지 않은 양상과 맞는다. 이것은 받을 수 있는 환불액이나 실제 미수신량을 뜻하지 않는다. 이 collector는 fetch 전에 state에 예약을 저장한 뒤 반환/포착 예외에서 계측값을 반영한다. 두 history에는 `window_collection_started`만 있고 실패·429·완료 이벤트가 없다. 정상 포착된 작업 종료라면 `finally`에서 `worker-result.json`을 쓰지만 둘 다 없다. 따라서 정상 완료·정상 회로 종료의 근거가 없으며 프로세스/호스트 중단 가능성이 있다.

**원인 확정 범위:** 현재 원장의 429 회로는 false이며 신규 잔여 예산은 2,361,454,891B다. 예산 소진이나 기록된 HTTP429가 이번 중단의 원인이라는 근거는 없다. Root가 OS 부팅·이벤트 로그를 별도 수집했다. 비정상 호스트 종료/재부팅 사실은 확인됐지만 이벤트가 가리키는 이전 종료 시각과 마지막 collector 파일 시각이 충돌하므로 정확한 종료 시각·직접 인과는 확정하지 않는다. OS 이벤트 근거는 `evidence/integration/collection-resume-host-events-20261018.json`을 참조한다.

원장의 마지막 수정 17:00:45와 실제 마지막 밴드 저장 17:04:17을 구분한다. 이전 상태 설명의 '17:00:45부터 수집 무변화'는 aggregate/원장 누계를 뜻하며 모든 부분 파일의 마지막 작업 시각은 아니다. 원장과 run-result의 68,157,440B 차이는 마지막 신규 예약이 run-result 저장보다 앞섰다는 구조와 일치한다. 이것만으로 누락 정산이나 실제 전송량을 확정하지 않는다.

## 기존 코드가 재시작을 막는 이유

1. 전체 collector용 `global-ledger.execution.lock`이 남아 있다. 파일이 있다는 사실만으로 프로세스 생존이나 소유자를 알 수 없고 이 파일은 비어 있어 PID도 없다.
2. lock을 통과하더라도 `CollectionLedger.reserve`는 이미 pending인 같은 key를 만나면 자동 재실행/환불을 거부한다.
3. 두 미완료 작업의 종료·전송·집계 근거가 없으므로 이전 작업을 정상 정산한 것처럼 복구할 수 없다.

잠금은 선점 후 초기 aggregate 검사 등에서 예외가 나면 정리 구문까지 도달하지 못할 여지도 있다. 다만 실제 pending 작업들은 이미 시작돼 부분 밴드를 저장했으므로 이번 잔존 lock을 그 초기 검사 문제만으로 설명할 수 없다. 이번 변경은 기존 lock의 자동 삭제를 추가하지 않는다.

## 구현과 사용 계약

`scripts/collect_training_parallel.py`에 `continuation_jobs(jobs, snapshot, enabled=False)`와 opt-in `--continue-unrelated-pending`를 추가했다.

- 기본값은 기존 job 목록을 그대로 유지한다. 기존 pending을 만나면 원래 원장의 fail-closed 동작이 유지된다.
- 옵션을 켜면 시작할 때 읽은 같은 global ledger의 pending key만 후보와 대조한다. 같은 key의 실제 config canonical SHA가 원장과 다르면 plan 저장 전에 거부한다.
- SHA가 일치하는 pending job만 실행 후보에서 제외한다. 원장·부분 파일·전체 예약·charged 값은 바꾸지 않는다. 입력 계획에 없는 pending도 관측 목록에 기록하지만 존재하지 않는 job을 제외했다고 표현하지 않는다.
- plan의 `pending_continuation`에 명시 옵션·관측 pending·제외 key·보존 예약을 남긴다. 정산 시도=false, 환불=0, lock handover=false다.
- 기존 settled job은 기존 `reserve`의 재사용/skip 계약으로 처리한다. 신규 key도 기존 원장과 동일 전체 예산에서 예약하며 3,000개 상한·전체 요청 최소 2초·최초429 공유 중단·2worker 정책을 그대로 사용한다.
- `--execute`가 없으면 계획을 쓰는 동작이다. 옵션만으로 다운로드하지 않는다. 실제 실행에는 `--execute`와 별도의 lock 소유권/프로세스 handover 증거가 필요하다. 이 helper는 lock 해제·정산·재수집·네트워크 요청을 수행하지 않는다.

실행 예시(실제 handover와 단일 실행자 확인 후 Root만 수행):

```powershell
python scripts/collect_training_parallel.py --candidate-plan data/first-group-training-esri-v2/lane-b-candidates.json --continue-unrelated-pending --max-batches 2 --execute
```

## 다음 실행 후보와 예산

실제 config를 생성한 검사에서 288개 후보 중 SHA가 일치하는 기존 pending 2개만 제외하여 286개가 남았다. 이 수치는 다운로드할 수량이 아니다. 기존 적격 공간창 제외·주별 정렬/교차배치·settled skip을 거친 다음 두 미예약 작업은 남술라웨시의 공간창03, 2021년과 2022년이다. 두 source 디렉터리는 조사 시 없었다. 정확한 config SHA·key·예산과 경로 존재는 `collection-resume-audit-20261018-next-jobs.json`으로 Root가 실행 직전 재확인한다.

두 작업의 전체 예약 상한은 합계 136,314,880B다. 기존 pending 예약 136,314,880B를 보존한 상태에서 신규 잔여는 두 추가 예약 후에도 2,225,140,011B다. 물리 패치는 현재 1,384개이며 두 작업이 명목상 16개씩 생성해도 1,416개로 3,000개 상한 안이다. 적격 패치 증가량과 클래스 보완 효과는 수집 결과를 검사한 뒤에만 말할 수 있다.

## 시험·문서·한계

### Root 최종 회귀와 통합 마감

Root의 신규7시험 별도 재실행은7 PASS/1.962초다. 전체 backend는 **1452건 중1450 PASS/2 SKIP/1046.064초/exit0**로 완료했다. 두 SKIP은 기존 복구의 외부 symlink 검사와146 CLI의 catalog symlink 검사에서 Windows 생성 권한이 없었던 것이다(후자는 오류1314). SKIP을 실제 링크 경계 검증 성공으로 표현하지 않는다. 집중·전체·담당 재실행은 겹치므로 합산하지 않는다. 원로그는 `collection-resume-root-focused-20261018.log`, `collection-resume-root-full-20261018.log`, 통합 검산은 `collection-resume-closeout-20261018.json`이다.

이번 변경은 내부 collector 큐의 명시 옵션으로 HTTP/UI 계약을 바꾸지 않았다. frontend 테스트·빌드를 이 변경 때문에 반복하지 않았으며147의280 PASS/build는147 이력이다. 별도150에서 기존 API localhost 모드를 복원하고 실제 GET·브라우저 연결/147 빈ID·catalog 보존을 확인했다. 구현/설계·사용법·시험·인계와 이해자료11개를 같은 단위로 반영한다. 전체 개발은 미완료이며 다음 작은256표적창 연결은 별도152 RFC의 PLANNED 범위다.

**TESTED_SYNTHETIC:** `tests/test_collection_continue_pending.py`의 신규 7개 시험은 PASS / 1.302초다. 기본 pending 재실행 거부, 명시 제외, config변경 거부, 입력/원장 불변, settled 기존 skip, 계획에 없는 pending 보존, 빈 큐의 실행0, 동일 예산과 기존 예약 보존/초과 거부를 Temp 원장으로 확인했다. 네트워크를 쓰지 않았다. 관련회귀·독립검토·운영 실행 증거는 Root가 아래 후속 절에 별도 확정한다.

**BLOCKED:** 기존 두 pending 자체의 정상 정산/완성은 여전히 불가하다. missing terminal을 합성해서 보충하지 않으며 metadata inspector/110 순수 계약을 실제 복구 coordinator로 부르지 않는다. 새 작업의 실제 수집 성공·학습 준비·모델 정확도·승인도 이 단위시험만으로 확정하지 않는다.

UI/API 계약 변경은 없다. 내부 collector 옵션과 plan 메타데이터만 추가하므로 화면 변경이나 브라우저 재검증은 필요하지 않다. 의미 있는 완료 후 Root는 이해 담당에게 완료 코드·시험·운영 관측을 전달해 해설·대본·FAQ·INDEX·변경 이력을 함께 갱신한다.

증거: `evidence/integration/collection-resume-audit-20261018-inspect.py`, `*-snapshot.json`, `*-recovery.json`, `*-terminal.json`, `*-aggregate.json`, `*-real-config-filter.json`, `*-next-jobs.py`, `*-next-jobs.json`, `*-focused.log`. 모든 신규 감사 파일은 이전 증거를 덮어쓰지 않는다.

## 2026-10-18 09:52 KST — 실제 두 작업으로 제한한 재개

Root가 사용자의 명시 재개 요청에 따라 단일 실행자로 handover를 수행했다. 기존 실행 lock은 삭제하지 않고 `data/collection-continuation-backup-20261018/global-ledger.execution.lock`으로 원본 이동했다. 원장·aggregate·run-result·기존 plan 4개는 원바이트 복사 후 SHA를 검산했다. 작업자 중복과 예산 거래 lock이 없는지 확인하고 이동 직전에 원장/legacy lock SHA와 프로세스를 다시 확인했다. `collection-resume-handover-20261018.ps1`의 PowerShell parser 오류0·Start-Process 호출1을 독립 확인했다. 기존 collector의 O_EXCL 실행 lock 획득은 그대로 유지한다.

실제 숨김 실행 PID는 **532**, 시작은 **09:52:13 KST**이며 `--continue-unrelated-pending --max-batches 2 --execute`다. **09:52:50 독립 관측에서 실제 신규 worker 2개 시작을 확인했다.** 남술라웨시2021-g03과2022-g03만 새로 예약했고 두 config SHA는 사전 next-jobs와 일치한다. 기존 pending2의 record 및 부분 파일·누락 terminal 상태는 그대로다. catalog·candidate·boundary·기본 config·과거 원장2개도 SHA 불변이고 backup4개 SHA도 기록과 일치했다. 429=false, stderr는 비어 있었다.

이 시점의 pending 총4개는 기존중단2개와 현재실행2개를 합한 것이다. 새2개가 미완료인 동안은 오류나 새중단으로 해석하지 않는다. 실제 worker_started는 수집 재개 근거이고 worker_finished·적격 패치 증가·학습 준비 완료의 근거는 아니다. 요청간격2초는 기존 코드 설정을 보존했으며 이 파일 관측이 패킷 단위 시간 측정을 뜻하지는 않는다.

독립 증거: `collection-resume-audit-20261018-independent-before.json`, `collection-resume-audit-20261018-observation-005250106967.json`, `collection-resume-audit-20261018-process-first.json`. Root의 실행 전 전체 baseline·handover/backup·실제 stdout/stderr는 `collection-resume-root-baseline-20261018.json`, `collection-resume-handover-20261018.json`, `collection-resume-live-20261018-stdout.log`, `collection-resume-live-20261018-stderr.log`를 참조한다. 이 운영 단위는 과거 미완료 두 작업 정산이나 journal 복구 성공과 구별한다.

### 09:54 KST 첫 작업 결과: 전송 성공, 다양성 정책 보류

2021-g03은 `worker_finished`로 종료했고 신규 패치는0개다. 이는 통신실패나 재개실패가 아니다. 실제 STAC·SCL 예비영상·동년 Esri 참조·교정 메타데이터를 받은 뒤 `reference_diversity_deferred`로 보류했다. 선택 영상의 구름은5.096%, SCL 예비valid는1.0이지만 확대 참조4,194,304픽셀 중 나무(class2)가4,131,175개(약98.49%)이고 현재 부족한 나지(class8)는4픽셀뿐이었다.

쉽게 말해 나지 보완이 필요한데 거의 숲뿐인 창을 발견했으므로, 추가6밴드 전체를 받아 패치 수만 늘리기 전에 기존 정책이 비용을 절약한 것이다. 해당 지역에 기존 적격 자료가 충분하고 같은 연도 적격도 이미 있을 때만 허용하는 보류 정책이며 이번 옵션이 새로 만든 기준은 아니다. 예비참조 분포는 최종256픽셀 패치·SCL·행정경계 적용 후 분포나 독립 정답 정확도와 다르다.

COG 본문983,040B+metadata 본문207,489B=1,190,529B로 새 작업만 정산됐다. source report의 upper와 measured가 같고 legacy0이며 worker metadata도 charged=read다. 이것은 해당 구현의 HTTP 본문 계측 범위이지 TLS/header 포함 전체 통신량 측정이나 기존중단2개 정산근거가 아니다. error·circuit은 없고 2022-g03은 실제 raw-B02 수신까지 진행 중이었다. 누계는1,384물리/1,111적격으로 아직 증가하지 않았다. 09:54:36 독립 증거는 `collection-resume-audit-20261018-observation-005436151520.json`이다.

### 09:58 KST 최종 결과: 신규16개 중11개 적격, 나지는 미보완

2022-g03은6밴드·마스크·동년 약한라벨 조립을 완료해16개 패치를 생성했고11개가 품질 적격이다. 2021은 위 다양성 보류로0개다. 기존 자료와 `patch_id`를 대조해 신규16개를 확인했다.

| 항목 | 재개 전 | 재개 후 | 변화 |
|---|---:|---:|---:|
| 물리 패치 | 1,384 | 1,400 | +16 |
| 품질 적격 | 1,111 | 1,122 | +11 |
| 품질 비적격 | 273 | 278 | +5 |
| train 적격 | 628 | 639 | +11 |
| val 적격 | 233 | 233 | 0 |
| test 적격 | 250 | 250 | 0 |

두 작업은submitted2/finalized2, `stop_reason=bounded_batch_count`, `circuit_open=false`로 정상 종료했다. PID532는 종료됐고 새 실행 lock은 정상 해제됐다. 원래중단된2개 pending만 그대로 남았다. 2022 작업의 source 상태는 `rgb_window_downloaded`, COG18,087,936B+metadata270,182B=18,358,118B다. 두 작업 합계 계상은19,548,647B이며 신규4GiB 예산의 잔여는2,341,906,244B다. 기존 예약을 환불해 얻은 잔액이 아니다.

**보완 효과의 한계:** 신규16개 전체와 적격11개 모두 나지(class8) 픽셀이0이다. 따라서 이번에는 수집 파이프라인이 실제 작동하고 학습 후보가11개 늘어난 것은 확인했지만, 나지 클래스 불균형이나 validation 나지256픽셀 조건을 해결하지 못했다. 추가 나지 후보와 누출 없는 분할·독립 라벨이 여전히 필요하며 학습은 실행하지 않았다. `learning_ready=false`다.

09:57:17 최종 독립 관측에서 기존 pending2 전체record와 부분파일/누락상태SHA, 기존 모든 settled record, catalog·candidate·boundary·기본config·과거원장2개 및 backup4개가 모두 보존됨을 다시 확인했다. 신규 key는 사전 검증한2개뿐이다. 증거는 `collection-resume-audit-20261018-observation-005717992597.json`, `collection-resume-audit-20261018-final-outcome.json`이다. 최초 outcome 집계 보조명령이 존재하지 않는 `id` 필드를 읽어 KeyError를 낸 것은 원본/수집기 오류가 아니며 쓰기 전 종료했다. 실제 필드 `patch_id`로 교정한 집계의 결과와 이력을 JSON에 남겼다.
