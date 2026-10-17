# Aggregate 출처·중복·누락 읽기 대조 — 2026-10-17

## 상태와 목적

**TESTED_SYNTHETIC:** 임시 JSON만 사용하는 16개 단위시험을 통과했다. **VERIFIED_REAL:** 실제 113참조·1,384행의 조사 결과는 root의 별도 실행 근거로 확정한다. **BLOCKED:** 원장과 aggregate의 원자적 정산·정확히 한 번 반영(exactly once) 증명·복구 실행은 미확인이다.

새 companion은 source_manifests, ledger report_path, 물리 patch 식별자와 source window의 메타데이터 연결을 읽어 누락·중복·모호성을 드러낸다. 기존 recovery/terminal/budget/collector 코어와 데이터·원장·lock·기존 계획 ID는 변경하지 않는다. raster 파일을 열거나 해시하지 않으며 정산·환불·재시작 기능이 없다.

## 구현과 실제 코드 계약

[recovery_aggregate.py](../../backend/app/data/recovery_aggregate.py)의 `inspect_recovery_aggregate(data_root)`는 고정된 `first-group-training-esri-v1/annual-window-report.json`과 `first-group-training-budget/global-ledger.json`을 읽는다. strict JSON·경로·fingerprint 보조 함수는 변경 없이 기존 terminal 모듈에서 재사용한다.

[collect_training_grid.py](../../scripts/collect_training_grid.py)의 `materialize_patches`는 다운로드 source row를 복사하여 patch_id·patch image_path를 새로 지정하고, 원본 image_path를 source_window.path에 보존한다. 같은 scene에서 여러 patch를 만들기 때문에 scene_id 반복은 중복 patch의 근거가 아니다. [collect_training_parallel.py](../../scripts/collect_training_parallel.py)의 finalize는 patch가 0개여도 report_path를 source_manifests에 기록할 수 있으므로 모든 report에 patch가 있어야 한다고 요구하지 않는다.

## 읽기 대조 항목

- source_manifests의 각 항목은 비어 있지 않은 문자열 경로여야 한다. canonical resolved 경로로 참조 중복을 찾고 파일의 MISSING/INVALID/PRESENT와 strict JSON scenes 형식을 기록한다. 같은 report가 반복 참조되어도 source row를 물리적으로 중복 생성한 것처럼 세지 않는다.
- ledger report_path는 현재 aggregate의 `sources/<batch>/annual-window-report.json` 범위만 양방향 비교한다. settled report가 목록에서 빠지면 SETTLED_REPORT_NOT_REFERENCED, 파일 자체가 없으면 별도 MISSING이다. pending report가 aggregate 목록에 있으면 PENDING_BATCH_REPORT_REFERENCED로 표시한다. pending에 report_path가 없을 때도 batch key의 예상 경로가 이미 참조됐는지 확인한다. 이 예상 경로를 확정된 ledger 신원 연결로 간주하지 않는다.
- 다른 실험 output의 ledger report_path는 OUT_OF_SCOPE이며 현재 aggregate의 누락으로 오판하지 않는다. 현재 범위 report 참조에 ledger 연결이 없거나 여러 batch가 같은 경로를 가리키면 SOURCE_REFERENCE_LEDGER_UNKNOWN/AMBIGUOUS로 기록한다. report_path가 없는 settled batch의 범위는 UNKNOWN으로 표시한다. 현재 범위 ledger 상태는 pending/settled 문자열만 허용하며 boolean·숫자·알 수 없는 상태는 INVALID issue다.
- aggregate scenes의 patch_id와 canonical image_path 각각의 중복 그룹을 찾는다. 잘못된 scene 형식이나 누락 식별자는 별도 issue다. 경로 canonicalization은 raster 바이트를 읽지 않는다.
- source report의 `status=rgb_window_downloaded` 행에서 `(image_path, scene_id)` 색인을 만든다. aggregate의 `(source_window.path, scene_id)`를 이 색인에 연결하여 UNIQUE_METADATA_MATCH/MISSING_MATCH/AMBIGUOUS_MATCH/UNKNOWN_IDENTITY_MISSING을 표시한다. 같은 scene에서 여러 patch가 한 원본 row를 공유하는 것은 정상이다.

이 연결은 **경로와 scene_id 두 필드만 검사**한다. 결과에 `scene_link_fields_checked`, `scene_year_province_binding=NOT_CHECKED`, `scene_year_province_checked=false`, `crop_window_identity_checked=false`를 명시한다. year/province/밴드/품질/좌표·window 크기·물리 crop 중복·raster SHA 연결 및 patch 완전성은 이번 범위의 검증이 아니다. UNIQUE_METADATA_MATCH를 전체 자료 신원이나 과학적 적격성 보증으로 표현하지 않는다.

## 안전 경계와 결과 해석

모든 report·patch·source 경로는 data root에 confined되어야 한다. root 밖·UNC/원격·위험 pending key는 안전하게 거부하며 외부 파일을 읽지 않는다. 모든 JSON에 duplicate key·비유한 숫자·잘못된 컨테이너 타입을 거부하고 boolean 식별자/경로를 문자열로 강제 변환하지 않는다. 전역 ledger/aggregate 형식 오류는 조사 자체를 실패시키고, 개별 source artifact 오류는 issues에 남긴다.

JSON 파일의 SHA·크기·누락 상태를 전후 비교한다. 같은 파일을 여러 번 읽을 때 초기 fingerprint를 덮어써 변경을 은폐하지 않는다. 원래 논리 경로→resolved target도 기록해 alias 재지정 시 거부한다. raster는 resolve만 하고 파일 바이트/존재/해시를 검증하지 않는다. 조사 자체는 여러 파일의 원자적 snapshot이나 프로세스 lock을 제공하지 않는다.

메타데이터 모순이 없으면 `metadata_consistency=CONSISTENT_METADATA`, 있으면 ISSUES_FOUND다. 어느 쪽이든 전체 `status=BLOCKED`, `exactly_once_applied=UNKNOWN`, 정산·실행·자동재개 권한 false, 환불0, 네트워크0, 원본쓰기0다. `raster_files_read=0`, `source_file_hashes_verified=false`를 유지한다. 실제 exactly once 증명에는 정산/aggregate journal 및 원자적 coordinator의 별도 설계·검증이 필요하다.

## CLI와 재현

[inspect_recovery_aggregate.py](../../scripts/inspect_recovery_aggregate.py)는 기본 stdout만 사용하며 CP949에서도 안전한 ASCII escape JSON/오류를 출력한다. `--output`은 프로젝트 evidence 아래의 새 파일만 허용하고 UTF-8로 저장한다. 기존 파일·입력 data root 아래 출력·evidence 밖 출력을 거부한다.

```powershell
python scripts/inspect_recovery_aggregate.py --data-root data
python scripts/inspect_recovery_aggregate.py --data-root data `
  --output evidence/integration/recovery-aggregate-live-20261017.json
```

exit0은 조사 성공이며 복구 실행 성공이 아니다. 개별 source 누락·조작은 issues가 있는 BLOCKED 보고서로 반환될 수 있다. 안전 경계·전역 입력 실패는 exit1이고 성공 evidence를 생성하지 않는다.

## 시험 근거와 인계

[시험](../../tests/test_recovery_aggregate.py), [로그](../../evidence/integration/recovery-aggregate-tests-20261017.log): **16 PASS (최종 시간은 로그 기준)**.

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend"
python -m unittest discover -s tests -p test_recovery_aggregate.py -v
```

같은 scene의 여러 정상 patch·원본불변·승인false, canonical 참조 중복, 누락/invalid/bool/중복키·비유한 JSON, 다른 실험 ledger 범위 제외, settled 누락과 pending 참조, reverse ledger unknown/ambiguity, patch 중복, source 신원 부족/불일치/다중연결, patch0 report 허용, root 이탈·원격, 반복 읽기 변경·missing 출현·논리 target 변경, CP949 CLI/new evidence/출력 보호를 검증했다. 독립검토 제안의 reverse ledger 대조와 현재 범위 status allowlist를 구현·시험에 포함했다. 독립시험은 전체 회귀에 중복 합산하지 않는다.

공개 API/화면 상태 계약을 변경하지 않는 내부 CLI여서 UI 코드 수정이나 실행 중 UI 서버 반영·브라우저 검증이 필요하지 않다. 화면에 결과를 연결하는 후속 작업은 web_ui에 명시적인 API·상태·오류 계약을 전달한 뒤 별도 검증해야 한다. root는 실자료 결과·보호 SHA·전체 회귀·원장/인계를 기록하고 이해 에이전트에 완료 코드·로그·한계를 전달한다. 관련 배경은 [문서24](24_collection_recovery_plan.md)와 [문서45](45_recovery_terminal_reconciliation.md)를 참조한다.

## Root 최종 실자료·전체 회귀 확인

**VERIFIED_REAL(로컬 JSON 메타데이터만):** CP949 환경의 [최종 CLI JSON](../../evidence/integration/recovery-aggregate-live-final-20261017.json)은 exit0 실행 근거다. 출처 참조113개가 모두 고유하고 존재하며, active1384행이 source_window.path와 scene_id 두 필드로 각각 하나의 원본 보고서 행에 연결됐다. 현재 범위 원장115건(보고서113+pending2)과 다른 실험4건을 구분한다. 참조/patch ID/이미지 경로 중복과 검사 범위의 issue는0이며 `CONSISTENT_METADATA`다. 그러나 status는 `BLOCKED`이고 연도·지역·crop 좌표 동일성과 raster는 미검사다. 이 중복0은 실제 영상 중복·기하 중첩·split 누출0을 뜻하지 않는다. exactly-once는UNKNOWN, 정산/자동재개 승인은false, 환불0이다. 초기 live는 원장 상태 allowlist 보완 전 기록으로 보존하며 최종 근거는 live-final을 사용한다.

[시험 후 보호 대조](../../evidence/integration/recovery-aggregate-live-integrity-20261017.json)는 누락 상태 포함132참조 불변·기존 계약7SHA 불변·기존 추적 코드/데이터/계약 변경0을 확인한다. 관련16 PASS·5.357초, 독립16 PASS·4.579초이며 [전체 회귀](../../evidence/integration/recovery-aggregate-full-tests-20261017.log)는 **372건/371 PASS/1 SKIP/71.714초/종료0**이다. 독립 실행을 전체372건에 중복 합산하지 않는다. SKIP은 기존 Windows symlink 생성 권한 제한이고 deterministic 경로 경계 시험은PASS다. 공개API/화면 변경이 없어 UI49건/build를 반복하지 않았다. 원본 manifest·원장·lock·분할·모델을 보존했고 신규 실자료 수집/학습은 실행하지 않았다.

## 후속 연도·지역·crop 메타데이터 companion

[문서47](47_recovery_crop_reconciliation.md)은 이 검사기에서 미검사로 남긴 year/province 원형 타입·값 및 window_in_source의 256px 정수 격자·동일 crop 식별자를 별도로 대조한다. 기존 이 검사기의 출력과 미검사 flags는 바꾸지 않으며, 별도 companion의 결과를 함께 읽어야 한다. 새 검사기도 raster 픽셀·실제 image bounds·다른 파일의 동일 내용·기하 중첩을 증명하지 않는다. 메타데이터 일치를 학습·정산·재개 승인으로 합산하지 않는다.

### 110 후속: commit 단계 선언 검사

[110 구현 문서](110_recovery_commit_contract.md)의 독립 순수 함수가 caller의 단계·세 target SHA·재관측·충돌을 검사한다. 기존 이 문서의 실자료 검사/형식·수집기·예산코드는 바뀌지 않았고 실제 journal/정산·집계/재개 coordinator는 미연결이다. 기존 pending2/예약·원장-run 차이를 해결하거나 exactly-once를 인증한 것이 아니다. 최종 신규14·관련66PASS/1SKIP·독립62PASS/1SKIP·보존 범위는 `evidence/integration/recovery-commit-contract-live-integrity-20261017.json`을 따른다. 해당 내부 선언 검사만 완료이며109의 실제 지속화/복구 수락 조건은 남는다.
