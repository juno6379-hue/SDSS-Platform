# 299 — 297 종료 후 신규 최대16개 감사 준비

상태: **VERIFIED_REAL / Root GO 후 단1 증분 감사 완료 / 신규16·적격15·나지0**. 아래 준비 절은 당시 기록이며 실제 결과를 마지막 절에 추가했다. 297 수집과 native 감사는 Root가 별도 승인한다. 이 단위는 기존285 원판을 보존하고 새297용 runner·최소 diff·문법 검증·문서·동결 지문만 만들었다. 운영 source/원장/래스터/모델 읽기0, HTTP0, collector0, native helper0이다. source1747/적격1376/gap11은 Root가 전달한 수집 전 기록값이며 새 성과가 아니다.

## 파일과 변경 범위

- 새 runner: `evidence/integration/deficit297-native-runner-root-20261018.py`
-285 원바이트 사본: `evidence/integration/deficit299-before285-native-runner-20261018.py`
- 최소 diff: `evidence/integration/deficit299-native-runner-vs285-20261018.diff`
- 동결: `evidence/integration/deficit299-native-preparation-freeze-20261018.json`

285 원본 및 archive는14334B/SHA `479dff23370e2db3fd58918e456fc9b263ad614afd3b69baa1f252a66011a4cb`다. 신규 runner SHA는 `a8a9ed9fcdbb0fafb60c3c71f028f188b6f855ccc5f7c6768a328c327da608ca`다. helper165의 준비 당시 코드 SHA는 `ba4da0b03bd19a0d327200a49eb5c75b28a1f42620be43c84826092c50c661ba`다. shared 제품을 수정하지 않았다. 메모리 compile만 수행했고 새 runner를 import/실행하거나 시험용 native를 수행하지 않았다.

기존285에서297 경로·old행1731→1747·정확2025/train job을 바꿨다. 추가한 사전 조건은297 전용 GO status·runner/helper SHA·launch/terminal raw SHA·종료/정산/중복 부재 선언·정확 source bytes 및128MiB cap·실제 신규 개수0–16이다. 고정 request canonical `e9ebe6f7dcbb986a853ed1749e97c4feafcacde1702c1937c946d7f6e2602487`, config semantic SHA `9d3618a258fbfd272c227cde90bffd3fc98fac2fd574864a69349a5825e41f71`, job `center1024-gorontalo-2025-e9ebe6f7dcbb-73cbb072`를 결속했다. 원 raw STAC datetime을 그대로 비교하며 연도2025도 확인한다. 추정 보정·반올림은 없다.

## Root 실행 전 필요한 실제 근거

Root는297 실제 종료·정산·잠금 해제·OS collector와 중복 감사 부재를 먼저 확인하고 원본 hold/추가 collector 금지를 유지한다. runner는 execution lock 부재를 직접 확인하지만 OS 전역 프로세스 탐지는 하지 않는다. GO의 중복 부재 boolean은 Root 관측 선언이며 독립 프로세스 증거를 대신하지 않는다. 현재 수집 전 source9d/ledger4a를 종료 후 실제 지문으로 재사용하면 안 된다. launch/terminal 미존재 시에는 실행할 수 없다.

아래는 계약 예시이며 **준비 승인 파일이 아니다**. null 값은 Root가 종료 후 실파일에서 채워야 하며 자동 생성·기존285 GO 재사용·자동 상향/재시도는 금지한다.

```json
{
  "status":"GO_297_BOUNDED_NEW_MAX16_NATIVE_AUDIT",
  "runner_sha256":"a8a9ed9fcdbb0fafb60c3c71f028f188b6f855ccc5f7c6768a328c327da608ca",
  "audit165_code_sha256":"ba4da0b03bd19a0d327200a49eb5c75b28a1f42620be43c84826092c50c661ba",
  "no_active_collector_or_duplicate_audit":true,
  "collector_terminated_and_settled":true,
  "launch_sha256":null,
  "terminal_sha256":null,
  "source_sha256":null,
  "source_bytes":null,
  "ledger_sha256":null,
  "expected_new_patch_count":null
}
```

승인 후에만 단1 실행한다.

```powershell
python -X utf8 -u evidence/integration/deficit297-native-runner-root-20261018.py --root-go E:/GeoAI–MLOps–SDSS/evidence/integration/deficit297-native-go-root-20261018.json
```

미래 GO 파일은 아직 만들지 않았다. 독점 `x` 생성 출력은 `deficit297-native-root-20261018.json`, `.log`, `-stderr.log` 세 개다. 기존 출력이 있으면 재시도하지 않는다. 예외는 issue_type와 trace/부분 결과를 보존하여 exit2이며 성공으로 바꾸지 않는다. 부분 출력 보존은 디스크 오류·프로세스 강제종료까지 보장하지 않는다.

## 0개와 양수 분기

launch/terminal·현재 source/ledger·고정 prior의 SHA와1747행 prefix/history를 읽기 검산한 뒤 신규 행 수를 Root GO와 대조한다. 0개면 helper0/래스터0으로 `ZERO_PATCH_REQUIRES_SEPARATE_ROOT_AUDIT`, native_validation_complete=false/exit2를 남긴다. 이는 정산·pending·새파일 부재까지 감사 완료한 결과가 아니다. Root가 별도0개 좁은 감사를 결정해야 한다. 사전차단/terminal exit!=0도 native helper 전에 중단하며 별도 Root 판단이다.

1–16개면 한 batch/동일 source1024·rgb_window_downloaded scene1이라는 기존285 계약 안에서만 helper165를 **한 번** 호출한다. helper는 새 patch만 검사하고 고정 old행·history·pending을 대조한다. 실제 scene이 여러 개거나 신규 미등록 물리파일이 있으면 성공으로 축약하지 않는다. helper 내부결과·원본/원장 drift 또는 lock 부재 검산이 실패하면 부분 보존한다.

## 유지하는 양수 감사

old prefix1747/history exact, 기존 pending entries 원문 exact와 reserved 합계를 보존한다. helper165가 selected batch settled와 worker charge=ledger charge=COG+metadata를 검사하며 마지막 stdout의 finalize attempt/settled/published 목록이 각각 정확[key]인지 대조한다. 부모 수집기의 예산/물리3000/2worker/2초/첫429·품질/split/support 보호는 변경하지 않는다. 감사 caller는 HTTP·수집·원장 쓰기를 하지 않는다.

새 patch 이미지/라벨/마스크 각각3파일×N, 최대48개의 native 품질을 검산한다. selected STAC raw SHA/ID/원 datetime/collection·연도/AOI bbox metadata containment/B02 URL의 저장참조 일치를 확인한다. raw B02와1024 source 첫 band 픽셀 동일,10m/6band/CRS/transform/quality grid와256 patch 첫 band·window transform 동일을 실제 로컬 MemoryFile에서 확인한다. TIFF magic을 먼저 검사하고 PROJ_NETWORK=OFF/GDAL aux 쓰기 비활성으로 로컬 bytes만 읽는다. caller URL로 원격을 열지 않는다. URL 비교는 저장 metadata 결속이며 원격 진실 검증이 아니다.

신규 patch 16개가 실제로 생기면 helper3×16=48 기록에 추가 trace21파일 중 patch image16개가 중복되어52개 고유 파일 구조가 기존285 관측이었다. 이번 N과 실제 trace 수는 결과에서 확정한다.52건을 사전 성공값으로 고정하지 않는다. 실제 patch directory 파일 집합을 등록 참조와 대조해 미참조파일을 숨기지 않는다.

나지는 raw label nearest 정렬→source quality 적용→최종 support mask 반영→eligible만 반영 순서로 patch별/합계를 구분한다. 품질 부적격 patch의 나지를 eligible 합계나 기여 수에 더하지 않는다. eligible contribution은 final 나지>=256 조건이다. 신규 취득·적격·나지 기여는 모두 미확정이며 실제 STAC metadata를 독립 정답/실영상 품질/학습 승인으로 확대하지 않는다.

## 한계와 다음 인계

source snapshot 개별 cap128MiB/ledger16MiB/원시 TIFF64MiB 등은 기존 helper/runner 한도다. 이 bounded 증분 감사는 전체128 JSON ContextVar 누적16GiB 후보QA와 서로 다른 계약이며 누적16GiB 계측을 추가했다고 주장하지 않는다. source 실제 bytes는 Root GO와 exact 대조하고 상한 초과 시 중단한다. 무제한 파일 탐색·운영 전체 래스터 재감사·기존 후보QA 반복은 없다.

준비물은 문법 검증만 통과했다. actual native completion, 실파일 SHA 개수, 나지, 정산 숫자는 실제 실행 이후 별도 보고한다. 현재 UI 기능 변경은 없어 화면 코드는 수정하지 않았고 실 API/브라우저도 실행하지 않았다. Root의 실제 감사 후 필요 새 고정후보QA/게시/API/UI 및 이해자료·대본FAQINDEX이력을 별도 증거로 인계해야 한다. 학습·registry·모델 변경은false/0이며 전체 개발 완료가 아니다.


## 실제 종료 관측과 단1 감사 — 2026-10-18 22:05 KST

Root가297 collector를 실행한 뒤 이 담당이 단일 종료 관측을 인수했다. launch21:58:15.020913 KST·collector14628/supervisor41744를 실제 OS에서 확인했다. 최초 로그0B/lock존재는 fresh 전검사 중 관측이며 worker/전송 성과로 세지 않았다. 이후 `deficit_worker_started` 신호를 확인했고22:04:07.327723 KST terminal exit0/350.39초를 관측했다. 마지막 stdout에 finalize/settled/published 각[key] 및 신규16/프로그램 적격15/22680361B가 있었고, collector·supervisor 부재/lock해제를 확인했다. 이때의 적격 수를 감사 전 확정값으로 확대하지 않았다. 종료관측 JSON은 별도 고정했다.

Root는 terminal/source/ledger/new16·정산·OS 중복 부재와300 독립정적검토 후 `deficit297-native-go-root-20261018.json` SHA `31f7f777da5b2e7d4f07352287157d6f42f1670b35eb5cef715aef9c4540324d`를 발급했다. 이 담당은 GO와 동결 runner SHA를 직접 대조한 뒤 위 승인 명령을 한 번 실행했다. exec session19511/exit0, helper165 실제 호출1/native_validation_complete=true였다. 빠른 종료로 감사 프로세스 PID를 별도 포착하지 못했으며 collector PID를 감사 PID로 재사용하지 않는다. helper 자체 seconds=4.474028은 helper 범위이며 raw trace를 포함한 전체 감사 wall로 표현하지 않는다. 별도 총 wall/RSS를 측정하지 않았다.

최종 결과 `deficit297-native-root-20261018.json`은34626B/SHA `e8c51e5c0afd86d4f0d89a58121103bad76ff3a5e4504079c41217ac08731096`, status `COMPLETED_BOUNDED_NATIVE_AND_TRACE_CHECKED`다. 원본과 후보 전체 QA는 수행하지 않았다.

| 항목 | 실제 결과 |
|---|---|
| 신규 patch / 적격 |16 /15|
| 현재 등록행 / 적격 |1763 /1391|
| 대상 cell 부족 / 전체 cell 부족 |0 /1|
| native 새 patch 래스터 |48개|
| helper file_sha_rechecks |52개, 검산 실패0|
| source trace 파일 / helper image 중복 |21개 /16개|
| 기존 prefix / history / pending2 |모두 exact 보존|
| pending reserved 합계 |136314880B 그대로|
| 원본/원장 audit 중 drift |false /false|
| 별도 collector/HTTP/운영 쓰기 |0 /0 /0|

현재 source SHA `9e63564c87647a144665bbb6bbe49b4a95d09bbd2c3bc0f3725861c54d5e7109`,68887373B; ledger SHA `574d382dd9da51ae56dc8fb135532f8f2e5c542b2c4cafdf73a6ee8dd9c6045f`를 승인 핀과 exact 대조했다. 기존 prefix1747행/history를 보존했고 source/ledger 두 읽기 안정성을 확인했다. 전체 셀 부족은11→1로 줄었지만 이 결과가 나지 대표성 충족이나 학습 승인이라는 뜻은 아니다.

실물 수는 시작 전 검증1748에 신규16을 더한1764로 추론하며 별도 운영 전체 디렉터리 재스캔은 하지 않았다. 등록행1763과 실물 추론1764를 섞지 않는다. 신규 patch 폴더의 실제48래스터와 등록 참조 집합이 일치하여 신규 미참조 patch 래스터0이다. 과거의 모든 미등록 파일을 이번에 해소했다고 주장하지 않는다.

### 출처·격자·품질과 나지

선택 scene은 `S2B_MSIL2A_20250629T021209_R060_T51NVA_20250629T035540`, 원 datetime은 `2025-06-29T02:12:09.024000Z`다. 저장 STAC/scene/row의 원문 datetime을 그대로 비교했고2025를 확인했다. 비영 소수초를 반올림하거나 strict246 시간정책을 완화한 작업이 아니다. 전체20 원시 feature를 독립 재생하지 않고 bounded filter summary와 선택 STAC bbox만 대조했다.

실제 source는 EPSG:32651/1024×1024/6band, transform `[10,0,442070,0,-10,88330]`이다. 저장 rawB02와 source 첫 band가 같고16개256 patch의 첫 band/CRS/window transform이 동일했다. SCL 후보 사전 유효율은0.96343994140625이며 최소0.65를 통과했다. 최종 품질은 helper의 patch별 valid80%·province95% 등 기존 조건으로15적격/1부적격이었고 품질 기준을 낮추지 않았다.

실제 나지는 raw label 정렬0→source quality 적용0→최종 supported0→eligible0, 기여 patch0이다. 부적격1개에서 나지를 적격 합계에 합치지 않았다. 새 적격15개가 늘어도 나지 부족3차단이 해소됐다는 근거는 없다. 새로운 후보 QA를 실행하지 않았으므로 현재 게시1360의 새source 대비 stale 해제나 새 후보 수를 확정하지 않는다.

### 정산·경계 및 후속

COG22413312B+metadata267049B=정산22680361B를 worker/원장/상태 파일과 대조했다. 잔여 예산은1822603826B다. finalize attempt/settle/publish가 단일 key에서 각각1회였고 기존 pending2를 환불·재정산하지 않았다. 감사는 read-only이며 기존4GiB/물리3000/2worker/2초/첫429/품질·split·support를 변경하지 않았다.

실행 후 추가 native/전체 QA·HTTP·모델학습·registry·게시 pointer 쓰기0이다. 이 감사의 `learning_ready=false`·`scientific_accuracy_validated=false`를 유지한다. 운영 snapshot은 순차 읽기 대조이며 원자적 DB snapshot이나 독립 정답 검증이 아니다. 준비 원문은 `deficit299-preparation-doc-before-native-20261018.md`에 원SHA로 보존했고 준비 freeze·285 원판·runner는 변경하지 않았다.

Root에 최종 result/핀/정산/나지0과 문서를 인계했다. 후속 새 고정후보QA/게시/profile/API/실브라우저는 Root가 별도 배정·실행한다. UI 코드를 바꾸지 않았고 이 감사 담당은 실제 API/UI를 확인하지 않았다. 이해 담당의 해설·발표대본·FAQ·INDEX·이력 갱신은 Root 별도 인계가 필요하며 여기서 완료했다고 표현하지 않는다. 남은 셀·나지/독립 정답·다른 모델 등 전체 개발은 계속 미완료다.
