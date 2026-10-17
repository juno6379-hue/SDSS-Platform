# 고정 manifest 기반 로컬 streaming SHA256 대조 — 2026-10-17

## 상태와 목적

**TESTED_SYNTHETIC:** 작은 로컬 byte fixture와1MiB 경계 fixture로15개 시험을 통과했다. **VERIFIED_REAL:** 기존 원본 manifest의 실제1475파일/총2332461937B streaming 결과는 root가 한 번 실행한 별도 근거로 확정한다. 구현/독립 시험은 실제 대용량 파일을 전수 읽지 않는다. **BLOCKED:** 픽셀 의미·라벨/품질·공간 독립성·모델 성능·정산/재개 승인은 미확인이다.

[문서48](48_recovery_raster_header_validation.md)의 헤더 검사는 전체 내용 SHA를 계산하지 않았다. 이번 별도 companion은 caller가 명시한 manifest SHA를 고정하고, 그 문서에 기록된 source 이미지와 patch 이미지 SHA를 실제 로컬 파일 바이트에 대조한다. 기존 코어/collector/모델/분할/원장/lock/데이터를 변경하지 않고 pixel decoder도 사용하지 않는다.

## 신뢰 입력과 사전 계획

[recovery_raster_content.py](../../backend/app/data/recovery_raster_content.py)의 `inspect_recovery_raster_content(data_root, expected_manifest_sha256, max_local_bytes=3GiB)`가 구현이다.

- 고정 경로는 `first-group-training-esri-v1/annual-window-report.json`이다. caller는 소문자64자리 SHA256을 명시해야 한다. 실제 aggregate SHA가 같아야 strict JSON을 읽고 nonempty scenes 계획을 시작한다. duplicate key·NaN/Infinity·overflow 비유한 수를 거부한다.
- 각 active 행에서 source_window.path/sha256과 image_path/patch_sha256.image만 수집한다. label/quality/이전 역사 행은 대상이 아니다.
- 모든 경로를 data root 안으로 canonicalize한다. 원격/UNC/VSI/root 이탈·일반 파일이 아닌 입력은 거부한다. 원래 논리 경로→resolved target도 저장한다.
- 기대 SHA가 누락되거나 형식이 틀리거나, 같은 canonical 경로가 상충 SHA를 가지면 전수 계획 단계에서 진단하고 **모든 content streaming을 시작하지 않는다**. 누락 파일도 FILE_MISSING/NOT_STARTED_PLAN_REJECTED로 남긴다. 다른 정상 파일을 먼저 해시한 뒤 상충을 발견하는 흐름이 아니다.
- 같은 canonical 경로는 역할(source/patch)·행 index를 합쳐 한 번만 해시한다. canonical 경로가 다른 hardlink는 별도 파일 경로로 읽고 결과에 나타난다. inode 동일성을 데이터 독립성으로 해석하지 않는다.
- 계획 stat의 고유 파일 크기 합이 총 local byte budget을 넘으면 파일 content 읽기 전에 실패한다. 예산은 정확한 정수1..3GiB이고 기본3GiB다. boolean/float/0/음수/3GiB초과 값은 거부한다. 실제 예상2332461937B를 포함하는 명시 예산3000000000B를 사용할 수 있다.

계획/경로/stat/aggregate JSON을 읽는 작업과 raster content streaming 예산은 구별한다. `max_local_bytes`와 `actual_local_bytes_read`는 대상 이미지 파일에서 반환받은 바이트를 세며, aggregate JSON 읽기나 파일시스템 메타데이터·OS 디스크 섹터/cache 동작을 계량하는 값은 아니다.

## streaming과 변경 방어

파일은 `open('rb', buffering=0)`로 열고 고정 chunk 상한1MiB로 읽는다. 매 요청은 `min(1MiB, expected file bytes remaining, total budget remaining)`이며 무인자 read()/전체 read_bytes()로 raster를 메모리에 올리지 않는다. 반환된 바이트를 즉시 누계·SHA256에 반영한다. 전체 계획 크기만큼 정상적으로 읽으면 실제 누계가 그 합과 같다.

파일별 expected size를 모두 읽은 뒤 총 예산에 여유가 있으면 최대1바이트 EOF probe를 한다. 반환된 probe 바이트도 예산에 포함하고 파일 성장으로 거부한다. 총 예산이 정확히 소진된 경우 추가 바이트를 읽지 않고 최종 fstat/stat의 동일 크기로 EOF 상태를 관측한다. 따라서 정규 파일이 성장하더라도 읽기 누계를 예산보다 늘려 확인하지 않는다. 조기 EOF·파일 성장·내용의 stat 변화·교체된 descriptor는 거부한다.

계획 stat(size/mtime_ns/ctime_ns/inode/device)과 open descriptor의 fstat, 읽기 전후 경로 stat을 대조하고, 종료 때 이미 읽은 파일도 다시 확인한다. 논리 경로 target과 pinned aggregate SHA도 재검사한다. 여러 파일의 원자적 snapshot이나 OS lock은 제공하지 않으며, 공격자가 내용을 바꾸고 관측 metadata까지 원복하는 상황을 막는 보장은 아니다. SHA 결과는 각 순차 읽기 관측의 근거다.

## 결과와 동일 digest 진단

파일별 expected/observed SHA, MATCH/MISMATCH, 역할·행 index·bytes_read·stat을 기록한다. 실제 SHA 불일치는 CONTENT_SHA_MISMATCH다. 다른 정상 파일도 읽고 결과를 남기지만, 처음 계획부터 잘못된 SHA·상충·누락이 있으면 전수 streaming0으로 끝낸다. `files`의 모든 MATCH가 기대값과 일치할 때 content_validation=RECORDED_SHA_MATCH다.

실제 읽은 SHA가 기대값과 일치한 파일만 digest별로 묶고 canonical 경로가 둘 이상인 그룹을 `same_digest_different_path_groups`로 반환한다. source/patch 역할을 각 경로에 명시한다. 기대 SHA만 같다는 이유로 그룹을 검증 완료로 표시하지 않는다. 동일 digest의 바이트 동일성 진단은 파일 표현에 관한 것이며 픽셀 의미·기하학적 독립성·split 적격성·모델 정확도를 뜻하지 않는다. 다른 압축/메타데이터의 같은 영상은 서로 다른 바이트 SHA를 가질 수 있다.

항상 status=BLOCKED, exactly_once_applied=UNKNOWN, ready_for_training/training_executed/scientific_accuracy_validated/settlement/execution/automatic_resume=false, 환불0·네트워크0·원본쓰기0이다. stdlib 파일 streaming만 사용하고 rasterio/GDAL/pixel decoder/sidecar/네트워크 요청을 사용하지 않는다. 기존 readiness/ML5 blocker·pending 정산 상태는 바뀌지 않는다.

## CLI와 시험

[inspect_recovery_raster_content.py](../../scripts/inspect_recovery_raster_content.py)는 필수 `--expected-manifest-sha256`, 선택 `--max-local-bytes`와 새 evidence 출력만 제공한다. 기본 stdout이며 Windows CP949용 ASCII escape JSON/오류, 파일 출력은 UTF-8이다. 기존/evidence 밖/data root 아래 출력은 **streaming 전에** 거부하고 exclusive create로 최종 생성 경쟁도 방어한다.

```powershell
python scripts/inspect_recovery_raster_content.py --data-root data `
  --expected-manifest-sha256 cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f `
  --max-local-bytes 3000000000 `
  --output evidence/integration/recovery-raster-content-live-20261017.json

$env:PYTHONPATH="$PWD\.runtime;$PWD\backend"
python -m unittest discover -s tests -p test_recovery_raster_content.py -v
```

exit0은 BLOCKED 읽기 조사 완료이며 정산/학습 성공이 아니다. 계획 진단/mismatch는 issue 보고서로 반환될 수 있고, 경로/예산/stale/global JSON 오류는 exit1이다. 기존 evidence를 덮어쓰거나 재실행을 통해 실제 큰 파일을 여러 번 읽지 않도록 새로운 출력 경로를 준비해야 한다.

[시험](../../tests/test_recovery_raster_content.py), [관련 로그](../../evidence/integration/recovery-raster-content-tests-20261017.log): **15 PASS, 1.477초**. pin/strictJSON·계획 전체 검증 후 stream0·상충/누락·정확 budget/초과/타입·canonical cache/역할합치기/서로 다른 hardlink·검증 digest그룹/불일치제외·고정 chunk/unbuffered·정확 budget 및1byte성장 probe·조기 EOF·descriptor 교체·이미 읽은 파일/manifest 변경·logical alias/missing출현·원격/root이탈/nonfile·CP949/new evidence/출력 보호를 검증했다. 원본 fixture bytes와 파일 목록 불변도 검사했다. 독립 시험은 전체 회귀에 중복 합산하지 않는다.

## UI와 인계

공개 API/화면 상태 계약 없는 내부 CLI이므로 UI 코드 수정·실행 중 frontend 반영·브라우저 검증이 필요하지 않다. 후속 화면 노출에는 web_ui에 확정 API·오류·상태·실제 근거를 인계해야 한다. root는 실제 대용량 streaming1회·보호 파일/원장/기존 계약 대조·전체 회귀·인계서를 담당하고 이해 에이전트에 완료 코드/시험/한계를 전달한다. SHA 일치를 전체 프로젝트 완료나 과학적 승인으로 표현하지 않는다.

## Root 실제 streaming·전체 회귀 확인

**VERIFIED_REAL(고정 manifest에 기록된 이미지 바이트만):** [최종 CLI JSON](../../evidence/integration/recovery-raster-content-live-final-20261017.json)은 CP949 환경에서 exit0이다. caller manifest SHA는 cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f다. 원본91+patch1384=1475파일을 실제 한 번 streaming하여 모두 MATCH/RECORDED_SHA_MATCH, 계획/실제 읽기2332461937B가 예산3000000000B 안에서 일치했다. issue0, verified digest의 다른 경로 그룹0이다. 바이트 그룹0은 장면·공간 독립성이나 전체 영상 중복0을 뜻하지 않는다. 픽셀 decoder/GDAL·네트워크 없이 읽었으며 status는BLOCKED, 라벨/quality·기하/성능·학습/정산/재개 승인false·exactly-once UNKNOWN이다.

[시험 후 보호 대조](../../evidence/integration/recovery-raster-content-live-integrity-20261017.json)는 보호132JSON/원장참조 SHA·존재 불변·기존 계약10SHA 불변·이전 추적 코드/데이터/계약 변경0을 확인한다. 1475raster stat/prefix16와1475부모 폴더 목록에도 변화가 없다. 실제 image 전체SHA 일치는 streaming 관측 시점에 한하며 여러 파일의 원자 snapshot/전체4335감사 또는 라벨/quality 검증으로 확대 해석하지 않는다.

관련15 PASS·1.477초, 독립15 PASS·2.365초이며 [전체 회귀](../../evidence/integration/recovery-raster-content-full-tests-20261017.log)는 **418건/417 PASS/1 SKIP/92.959초/종료0**이다. 최종15시험은 전체 발견 전에 작성돼418건에 포함됐으며 추가 전체 재실행은 없었다. 독립 실행과 별도 earlyEOF 보완 실험을418건에 중복 합산하지 않는다. SKIP은 기존 OS symlink 권한 제한/deterministic 경계 시험은PASS다. UI49건/build는 공개API/화면 변경이 없어 반복하지 않았다. 신규 다운로드/수집/실자료학습/정산/환불/재개/배포는 없다.

## 후속 보조자산 진단

[문서50](50_recovery_auxiliary_content_validation.md)은 명시된 label/quality/boundary2855파일의 별도 SHA 대조와 legacy80행 역할별미기재 UNKNOWN을 다룬다. 본 문서의1475image범위와 구분하며 과거4335파일 전체감사나 라벨의미·학습승인으로 확대하지 않는다.
