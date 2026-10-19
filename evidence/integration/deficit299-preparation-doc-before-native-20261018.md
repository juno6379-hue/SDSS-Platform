# 299 — 297 종료 후 신규 최대16개 감사 준비

상태: **PREPARED / ROOT_NATIVE_GO_REQUIRED / 실제 감사0**. 297 수집과 native 감사는 Root가 별도 승인한다. 이 단위는 기존285 원판을 보존하고 새297용 runner·최소 diff·문법 검증·문서·동결 지문만 만들었다. 운영 source/원장/래스터/모델 읽기0, HTTP0, collector0, native helper0이다. source1747/적격1376/gap11은 Root가 전달한 수집 전 기록값이며 새 성과가 아니다.

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
