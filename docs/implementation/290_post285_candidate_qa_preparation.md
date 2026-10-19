# 290 — 285 후속 고정 후보 QA 실행 준비

현재 상태: **VERIFIED_REAL / 단1 실제 QA 및 인계 검산 완료 / 후보1360·학습준비 false**. 아래 준비·시작 계약은 당시 기록이며 최종 결과를 마지막 절에 추가했다. 준비 원문은 `evidence/integration/priority290-preparation-doc-before-start-20261018.md`에 SHA `fb5726916211a77edb54e5ac447e24b583d2ac0f22d8be9953835c3c9052bd0b`로 보존했다. 준비 freeze와 runner/prep는 변경하지 않았다.

준비 당시 상태는 PREPARED / ROOT_GO_REQUIRED / 실제 QA 미시작이었다. 기존273 runner/prep/freeze/완료 근거·문서는 수정하지 않았다. 운영 제품·원본·원장·모델·split·게시 pointer 쓰기0, HTTP/collector/학습0이다. 준비에서는 Root가 지정한 source·ledger·policy의 metadata SHA와 크기를 실제 읽어 검산했고 이미지·라벨·모델은 읽지 않았다. Root GO 이후 단1 QA만 허용된 고정 cohort를 읽는다.

## 직접 확인과 미확정값

Python QA/collector 명령을 실제 OS에서 조회하여 prepare_priority_candidate164/priority273·290 runner/collect_deficit_guarded에 해당하는 실행 프로세스0, execution lock 부재를 확인했다. 조회 셸 자신은 실행 QA로 세지 않았다. Root GO 시 다시 확인해야 하며 과거 관측을 미래 실행 허가로 사용하지 않는다.

| 입력 | bytes | 실제 확인 SHA256 |
|---|---:|---|
| current source | 68220381 | `9d491e6ede51cf29407add25b83919cc5d4150576a694c5019814b973d20c2b7` |
| current ledger | 67545 | `4a4f4a47b522b9497b944ac00b29d2368a977c1a4eb6dfe972a34959fcc68722` |
| 고정 policy | 1306 | `01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7` |
| 285 단일 감사 | 준비 JSON에 크기 기록 | `194affdac6f8838875251bdb8c6cb2807cc3492015b3b655ba71ae040ba8c455` |

source는 **64MiB67108864B보다1111517B 크다**. 파일 크기로 자동 상향하지 않으며 정확한 명시128 profile을 Root가 승인해야 한다. 단일 native 감사 status는 `COMPLETED_BOUNDED_NATIVE_AND_TRACE_CHECKED`다. 감사 자체를 재실행하지 않았다.

Root의 원본 보고값은1747행/적격1376(train834/val292/test250)이다. 준비는 이를 전체 source QA로 다시 계산한 작업이 아니다. **새 후보 수·제외량·최종 blocker·나지·준비도는 미확정**이며 prep에 candidate_count=null을 남겼다. source의 scenes+history 합계3000 검사는 실제164의 profile reader에서 수행한다. 준비 중 원본 전체를 JSON parse하거나 history 수를 발명하지 않았다.

현재1348 게시 pointer와 `candidate-receipt275-20261018.json`의 SHA는 둘 다 `1aee2e01583a024c508d6fdac0d3c4fac2260bbd449ea12269d5e033c1dcc7b4`다. 새 runner가 시작 전 이 expected 지문과 일치하는지 확인하고 끝난 뒤에도 보존을 검산한다. 게시나 receipt 갱신은 수행하지 않는다.

## 273과 같은 실제 실행 계약

새 파일은 `evidence/integration/priority290-{preparation,runner}-20261018.{json,py}`이며 실제 이름은 각각 preparation JSON과 runner PY다. `priority290-runner-vs273-20261018.diff`에 검증된273 runner 대비 차이를 남겼다.

차이는 새290/run-id·준비 SHA·285 native/source/protected receipt 맥락, 그리고 `protected == plan['protected_expected']` 시작 전 확인이다. 기존164 CLI `main(argv)` 호출 지점은1개이며 코드16개 지문은273 당시와 실제 일치한다. 공유 제품을 바꾼 것이 아니다. AST parse/compile만 수행했고 runner/CLI를 실행해 시험하지 않았다.

명시 profile은 `bounded128m-3000-v1`, descriptor SHA `db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4`다. source/candidate128MiB, scenes+history3000행, depth32/node4000000, 누적 JSON I/O17179869184B(16GiB), 역할별 policy1MiB/receipt64KiB/readiness16MiB/saved_plan4MiB를 유지한다. node 검사는 decode 후이며128MiB가 최대 RAM/RSS·실행시간을 보증하지 않는다.

runner의 한 ContextVar scope에서 준비 JSON2회 읽기·Root GO·감사 SHA·보호 pointer 전후·launch/log/terminal·source snapshot→source QA→split 계획/검산→package/stage→candidate QA→실 verified_files SHA→summary가 같은 budget을 사용한다. 중첩 @profile_entry는 기존 budget을 재사용한다. app/backend alias의 공용 state와 세 v2 receipt/정확 marker 후검산도 그대로다. source/policy는164가 출력 전·QA 뒤·최종에 다시 직접 검산한다.

원장 SHA는 준비/Root native 완료 provenance이며 **QA 입력으로 추가하지 않는다**. Root가 GO 직전 최신 원장/정산을 확인해야 한다. 준비 때의 별도 metadata 지문 읽기를 미래 실행의 profile 측정치로 꾸며 쓰지 않는다. 실행 scope는 실제 호출의 측정값을 남긴다.

## 단1회 실행과 새 경로

run-id는 **guarded290-20261018**다. 다음 새 경로가 모두 미존재임을 준비 시 재확인했다.

```text
data/priority164-guarded290-20261018/
evidence/integration/priority164-guarded290-20261018/
evidence/integration/priority164-guarded290-20261018.log
evidence/integration/priority290-launch-20261018.json
evidence/integration/priority290-terminal-20261018.json
```

GO 뒤 다시 검사하며 기존/부분 파일을 삭제하거나 재사용하지 않는다. 승인 파일이 없으면 필수 argparse 인자가 없어 QA를 실행할 수 없다. Root가 전체 runner/최소 diff/핀을 검토한 뒤 아래 명령을 단1회 승인할 수 있다. **현재 이 명령은 미실행이다.**

```powershell
python -X utf8 -u evidence/integration/priority290-runner-20261018.py --approval 'E:/GeoAI–MLOps–SDSS/evidence/integration/<ROOT_290_GO_FILE>.json'
```

GO는 아래 정확 key 집합/값을 요구한다. 예시 자체는 승인 파일이 아니다. bool3개는 실제 true여야 한다.

```json
{
  "kind":"PINNED_CANDIDATE_QA_290_GO",
  "approved":true,
  "run_id":"guarded290-20261018",
  "preparation_sha256":"e9260f8ee5c81a63a9a8221e24b439f5e7c0b2b5e5955129be6b0cf169ace4ef",
  "native_audit_sha256":"194affdac6f8838875251bdb8c6cb2807cc3492015b3b655ba71ae040ba8c455",
  "source_sha256":"9d491e6ede51cf29407add25b83919cc5d4150576a694c5019814b973d20c2b7",
  "source_bytes":68220381,
  "manifest_profile":{"name":"bounded128m-3000-v1","sha256":"db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4"},
  "no_active_collector":true,
  "execution_lock_absent":true
}
```

runner는 source bytes·code16핀·native 근거 SHA·lock·새 경로·기존1348 pointer expected를 검사하고 한 프로세스에서 기존 CLI main을 한 번 호출한다. OS 전체 collector 탐지는 Root 확인을 대체하지 않는다. source/pointer/code가 달라졌다면 준비를 자동 수정하거나 재시도하지 않는다.

## 완료 검산과 미완료 경계

실행 후 actual wrapper wall과 CLI+postcheck wall을 구분하고 RSS를 관측하지 못하면 false/null로 남긴다. 느린 strict metadata 단계를 우회하지 않는다. failure/상한 초과는 부분 보존/exit2이며 cap 증가·새 profile·자동 retry0이다. 예산 소진/쓰기 실패이면 terminal도 없거나 부분일 수 있고 예산 밖 fallback 완료 영수증을 쓰지 않는다.

정상 exit라도 source/candidate의 실제 split/eligible·sameScene 제외/partition·파일5376 같은 기록 수는 **이번 결과를 읽어 새로 확정**해야 한다. 이전273 개수를 이번 값으로 고정하지 않는다. 나지3 차단·NOT_CAPTURED_BUDGET도 과거 참고이며 새 gate를 관측대로 기록한다. 수집 증가를 독립 정답이나 학습 승인으로 확대하지 않는다.

새 summary/terminal/세 v2 receipt·actual output SHA·원본/정책·보호 pointer와 exact retained partition을 읽기 검산하고, Root에게 검산 종료 신호를 보낸다. Root의 독립 승계·old1348 archive·게시/명시 source 재결속·실 API/브라우저·이해자료/INDEX/이력은 별도 근거로 마감한다. 이 내부 준비는 화면 변경이나 실제 QA 완료가 아니므로 API/UI를 실행하지 않았다.

## 실제 시작 — 2026-10-18 21:16 KST

Root가 전체 runner/273 최소 diff/16현재코드핀/준비 freeze와 source·ledger·policy·native·2pointer·새 경로를 확인하고,292 독립 검토에서 추가 차단이 없음을 확인했다. 명시 GO `priority290-go-root-20261018.json` SHA `b6e06319c864de66f7a94801e1f32d530288bec49d043734d6e3105693c295f5`를 발급했다. 승인 직전 중복 QA/collector0·lock 부재, 원본 hold·추가 collector0을 Root가 재확인했다.

동결 runner `68b271471887eca7259dd72196a1515ecef57a50239f25ba917ea194c3877c3e`와 GO 지문을 직접 확인한 뒤 명령을 **한 번** 실행했다. 실제 PID25528/exec session5248, launch21:16:15 KST다. 실행 명령은 위 template의 approval을 실제 절대 `E:/GeoAI–MLOps–SDSS/evidence/integration/priority290-go-root-20261018.json`으로 지정했다.

21:16:41.654 KST 로그의 `SNAPSHOT_PINNED`로1747행/source9d491 지문 고정을 실제 확인했다. 아직 source QA/후보 생성·QA/최종 SHA/summary/terminal이 끝나지 않았으므로 **후보 수량·gate는 미확정**이다. 이 시작을 완료나 학습 승인으로 표현하지 않는다. 자동 retry·상한 증가·추가 동일 native 감사·게시·모델 변경은0이다.

초기 OS 표본은 Windows WorkingSet443355136B/PeakWorkingSet443355136B였다. 이는 해당 표본의 실제 Windows 값이며 Linux RSS나 최종 peak/최대 메모리 보장이 아니다. runner 자체는 RSS를 관측하지 않으며 완료 시 범위를 구분한다. 기존 log/receipt 단계의 최소 읽기와 프로세스 상태만 관측하고 최종 QA까지 이 담당이 소유한다.


## 실제 완료 및 Root 인계 — 2026-10-18 21:41 KST

단일 runner PID25528/session5248이 exit0으로 종료했다. terminal 시각은21:40:19.460 KST이며 전체 wrapper1443.969초, CLI+후검산1442.547초다. source QA326.406초와 candidate QA 함수330.187초는 전체 시간과 별개다. 후보 QA 함수에는 입력 증거 검산도 포함되므로 순수 래스터 처리 시간으로 해석하지 않는다. 중간 strict JSON 구간이 길었으나 profiler 없이 특정 병목 원인을 확정하지 않았다. 자동 재시작·상한 확대·추가 QA0이다.

| 구분 | 전체 등록행 | train 적격 | val 적격 | test 적격 | 적격 합계 |
|---|---:|---:|---:|---:|---:|
| 21:16:41.654 고정 source |1747|834|292|250|1376|
| 최종 고정 후보 |1731|834|276|250|1360|

scenes+history 검산에서 source/history는1747/0, candidate/history는1731/0이었다. 후보는 이전273의1348보다12개 늘었으며 train만822→834다. 전체 등록행과 학습 조건을 통과한 적격 수는 구별한다.

동일 scene `S2A_MSIL2A_20210812T025551_R032_T48MXT_20210812T132431`이 banten과west_java 그룹의 고정 split 경계를 넘는 문제에 대해 test를 유지하고 val의 source 행 인덱스288–303 총16개를 **후보에서만** 제외했다. 원본 행·운영 split은 변경하지 않았다. 후보 retained rows의 원문 일치·lineage·완전 partition을 검산했고 남은 source identity conflict0이다. 원본의 해당 blocker1개가 제거되어 원본4차단에서 후보3차단으로 줄었다.

원래164 CLI가 실제 파일 기록5426개의 SHA를 다시 검산하여 불일치0을 확인했다. 후속 metadata 인계는 동일 래스터 감사/QA를 반복하지 않고11개 출력 지문 불일치0 및 세 schema_version2 영수증의 정확128 marker를 검산했다. package/stage 후보는 둘 다 SHA `72c7385708ac824b0ff67da9bb72391f33d7f6f63fa942da4d01c46c50dc6961`다. 최종 summary SHA `6a313637000e3badc25cf35ecd28f6f516a0dda3f276fdbc781c30a795f3badd`, terminal SHA `efbaf7b473a4b56320a8cd487c99f7f074d7de07136013b66e7871e0a81222e4`다.

### 크기·누적 계측 및 보존 경계

source68220381B는 default64MiB보다1111517B 크고 후보67599006B도490142B 크다. 양쪽 모두 처음부터 승인된 `bounded128m-3000-v1`을 동일 ContextVar scope에 명시하여 snapshot→원본 QA→계획→package/stage→후보 QA→최종 출력과 인계까지 처리했다. 크기에 따른 자동 선택·기본64 우회·예외 상향이 아니다. 128MiB·3000행·depth32·node4000000·누적16GiB와 역할별 개별 cap을 유지했다.

terminal 쓰기 직전 read4359798569B/write206296555B/합4566095124B였다. terminal 및 후속 metadata 검산/proof 쓰기를 포함한 QA+handoff 합계는4977946640B로17179869184B 이내다. 문서·완료 freeze 작성은 QA 계측 완료 후의 행정적 인계 산출물이며 이 수치에 포함한다고 주장하지 않는다. 후속 checker는 이전 계측을 이어받아 잔여 budget 안에서만 수행했다.

인계 checker session33861 exit0, proof 시각21:41:39.798 KST다. `handoff-verification.json`은6636B/SHA `55867bcd85b3a888d24db95a7251e688d1eef829d062a45f0458f16d5f7ec2c6`이다. 이 시각 source9d491·policy01991·ledger4a4f 지문이 준비와 일치했고 기존1348 pointer 및 receipt275의 SHA `1aee2e01583a024c508d6fdac0d3c4fac2260bbd449ea12269d5e033c1dcc7b4` 보존을 확인했다. Root에 검산 종료/승계 대기 해제 신호를 전달했다. **이후 Root293/294의 의도된 게시·profile 변경은 별도 작업**이며 이 문서는 미래 pointer 불변을 주장하지 않는다. 인계 뒤 운영 원본·원장·pointer를 다시 읽지 않았다.

실행 중 OS 관측 PeakWorkingSet 최댓값 표본은1307496448B였다. 최종 peak 보장이나 Linux RSS가 아니며 wrapper의 rss_observed=false를 유지한다.

### 나지 개선과 학습 준비도의 한계

| split | valid label pixels | 나지 pixels | 나지 비율(%) | 기여 patch |
|---|---:|---:|---:|---:|
|train|53118025|2562|0.0048232214959046385|1|
|val|17776457|2998|0.01686500296431398|2|
|test|16252940|1025|0.006306551307025068|0|

나지 픽셀과 기여 patch는 이전273과 같다. train 적격 수는 늘었지만 나지는 늘지 않아 분모 증가에 따라 train 나지 비율은 오히려 낮아졌다. 각 split의 나지 비율0.5%·기여5 기준을 충족하지 못해 `REFERENCE_CLASS_IMBALANCE`가 split별3건 남았다. test의 나지 픽셀1025개와 기여 patch0은 모순이 아니라 기여 인정 기준을 통과한 patch가0이라는 뜻이다. 일반 지역·연도 수량 보완과 나지 대표성 보완은 별도다.

`ready_for_training=false`, `observed_gate_ready_for_training=false`, `scientific_accuracy_validated=false`, `training_executed=false`, registry 호출0/HTTP0을 유지한다. 약한 참조 라벨 분포 검사는 독립 정답·실영상 품질·과학적 정확도 검증을 대신하지 않는다. connectivity는 `NOT_CAPTURED_BUDGET`이며 공간 연결성 전체 검증을 완료했다고 표현하지 않는다. 추가 collector/native 감사/모델 학습·원본/원장/모델/split 쓰기0이다.

### 다음 인계와 UI 경계

완료 freeze에11출력의 인계 당시 실제 지문과 runner/prep/GO/로그/summary/terminal/checker/proof/이 문서 지문을 고정한다. 기존273 원판·준비 archive·runner/prep freeze는 보존했다. 이 단위는 제품 코드나 화면을 바꾸지 않았으며 게시·실 API·브라우저는 실행하지 않았다. Root293 승계→294 명시 profile 재결속/실 API→web_ui 실제 브라우저 확인을 별도 담당 증거로 마감해야 한다. Root에는 본 문서/실행 증거를 이해 담당에 전달하여 쉬운 설명·발표 대본·FAQ·INDEX·변경 이력을 갱신하도록 인계했다. 그 후속을 이 담당이 완료했다고 주장하지 않는다. 전체 개발·남은 수집·학습 준비는 계속 미완료다.
