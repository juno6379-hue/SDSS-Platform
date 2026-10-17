# 보조자산의 명시 SHA와 부분 커버리지 읽기 대조 — 2026-10-17

## 상태와 목적

**TESTED_SYNTHETIC:** 작은 byte fixture만 사용하는14개 시험을 통과했다. **VERIFIED_REAL(계획 메타데이터):** 고정 manifest에는 patch label1,384개·patch quality1,384개·source quality86개·boundary1개로 고유2,855파일/12,719,583B가 기록되어 있다. source-quality와boundary 참조가 없는 레거시80행은 역할별80개 UNKNOWN으로 남긴다. 실제 보조파일 streaming은 root만 한 번 수행하여 별도 근거로 확정한다. **BLOCKED:** 라벨 의미·quality 적합성·행정경계 승인·독립 공간/성능·정산/재개는 미검증이다.

[문서49](49_recovery_raster_content_validation.md)의 이미지 SHA 검증과 별도로, 이번 companion은 명시된 보조자산 SHA만 읽기 대조한다. 경로나 기대 SHA를 다른 행/기본경로에서 추정하지 않고 원본 manifest를 보완하지 않는다. 기존 image/terminal/aggregate/crop/header/collector 코어·원장·lock·분할·모델을 변경하지 않는다.

## 입력·역할·전수 계획

[recovery_auxiliary_content.py](../../backend/app/data/recovery_auxiliary_content.py)의 `inspect_recovery_auxiliary_content(data_root, expected_manifest_sha256, max_local_bytes=64MiB)`는 고정 `first-group-training-esri-v1/annual-window-report.json`을 caller의 소문자64자리 SHA256으로 pin한다. strict JSON의 duplicate key·비유한 수·잘못된 전역 형식을 거부한다.

| 역할 | 경로 | 기대 SHA |
|---|---|---|
| patch_label | row.label_path | row.patch_sha256.label |
| patch_quality | row.quality_mask_path | row.patch_sha256.quality |
| source_quality | row.source_window.quality_mask_path | row.source_window.quality_mask_sha256 |
| boundary | row.source_window.boundary_path | row.source_window.boundary_sha256 |

양쪽 키가 모두 미기재면 UNKNOWN_REFERENCE_ABSENT다. 레거시 source_quality/boundary가 이 경우이며 명시된 다른 파일의 검사를 막지 않는다. role_coverage에 recorded_reference_rows/unknown_reference_rows/unique_planned_files를 구별하고 unknown_references에 행/역할을 기록한다.

한쪽 키만 기재된 partial pair는 PARTIAL_REFERENCE로 plan INVALID이며 streaming0이다. 명시된 null/boolean/빈경로/잘못된 SHA·container도 INVALID다. 즉 키 자체가 없는 레거시와 명시값이 손상된 자료를 같은 UNKNOWN으로 무시하지 않는다. 같은 canonical 파일 경로가 상충 SHA를 갖거나 파일 자체가 없을 때도 전수 계획에서 전체 streaming을 시작하지 않는다. 누락 파일은 FILE_MISSING으로, 미기재 참조와 구분한다.

모든 명시 경로는 data root 안의 일반 로컬 파일이어야 한다. 원격/UNC/VSI/root 이탈을 거부하고 논리 경로→resolved target을 추적한다. 같은 canonical 파일을 여러 행/역할이 공유하면 한 번만 해시하고 roles/references를 합친다. 실제 SHA를 읽기 전에 고유 파일 stat 크기의 합이 총예산 안에 있는지 검사한다.

## streaming·예산·내용 결과

기존 [image streaming 코어](../../backend/app/data/recovery_raster_content.py)의 `_stream_sha`, `_file_stamp`, `_sha_valid`를 변경 없이 읽기 재사용한다. 기본/최대 보조예산은64MiB이며 caller는1..64MiB의 정수만 지정할 수 있다. boolean/float/0/음수·상한초과는 거부한다. 고정 최대1MiB의 unbuffered read, 반환바이트 예산 누계, 조기EOF/성장, descriptor fstat·읽기 전후 stat·최종 재검사를 상속한다. 정확 예산이 소진되면 추가 EOF probe를 읽지 않으며 fstat/stat의 크기를 대조한다.

byte budget은 대상 보조파일에서 반환받은 바이트이고 aggregate JSON·파일시스템 metadata·물리 디스크 sector/cache 계량은 아니다. manifest SHA와 논리 경로 target도 종료 시 다시 확인한다. 순차 읽기 관측이며 원자적 snapshot·운영체제 lock 보장은 없다.

content_validation과 coverage_status는 별개다.

- 모든 필수 계획이 유효하고 미기재도 없으면 RECORDED_SHA_MATCH/COMPLETE_REFERENCES다.
- 명시된 파일이 모두 일치해도 미기재 역할이 있으면 RECORDED_AVAILABLE_SHA_MATCH_PARTIAL/INCOMPLETE_REFERENCES다. 모든 역할 검증 완료로 표현하지 않는다.
- 모든 역할이 미기재여서 검사 대상0개면 NO_RECORDED_REFERENCES/read0이다. 빈 검사를 SHA MATCH로 표시하지 않는다.
- partial/malformed/conflicting/missing file은 NOT_STARTED_PLAN_REJECTED/PLAN_INVALID, streaming0이다. 유효 계획에서 실제 SHA가 다르면 ISSUES_FOUND이고 coverage는 별도 유지한다.

실제 해시가 기대 SHA와 일치한 파일만 동일 digest의 다른 경로 그룹에 포함하며 역할을 명시한다. label/quality의 동일 바이트 진단은 클래스 의미·QA 적합성·독립 표본의 증거가 아니다. boundary SHA가 일치해도 공식 경계나 행정 승인·기관 권한을 검증한 것이 아니다.

항상 status=BLOCKED, exactly_once_applied=UNKNOWN, ready_for_training/training_executed/scientific_accuracy_validated/settlement/execution/automatic_resume=false, 환불0·네트워크0·원본쓰기0이다. pixel_decoder_used/label_semantics_validated/quality_suitability_validated/boundary_authorization_verified/geometric_independence_checked도 false다. rasterio/GDAL·픽셀 해석·sidecar 쓰기를 수행하지 않는다.

## CLI와 시험 근거

[inspect_recovery_auxiliary_content.py](../../scripts/inspect_recovery_auxiliary_content.py)는 필수 manifest pin과 선택 예산/새 evidence 출력만 제공한다. stdout/stderr는 CP949에서 안전한 ASCII escape, 파일은 UTF-8이다. 기존 파일·evidence 밖·입력 data root 아래 출력은 streaming 전에 거부한다.

```powershell
python scripts/inspect_recovery_auxiliary_content.py --data-root data `
  --expected-manifest-sha256 cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f `
  --max-local-bytes 67108864 `
  --output evidence/integration/recovery-auxiliary-content-live-20261017.json

$env:PYTHONPATH="$PWD\.runtime;$PWD\backend"
python -m unittest discover -s tests -p test_recovery_auxiliary_content.py -v
```

exit0은 읽기 진단 보고서 생성이며 BLOCKED가 유지된다. 개별 내용 불일치·부분 커버리지·계획 진단은 보고서로 반환할 수 있고, 경로/예산/stale/global JSON 오류는 exit1이다.

[시험](../../tests/test_recovery_auxiliary_content.py), [로그](../../evidence/integration/recovery-auxiliary-content-tests-20261017.log): **14 PASS, 3.996초**. 네 역할의 byte 검증·cache/동일path 다역할·원본 bytes/목록 불변·전체 승인false, 레거시 미기재와 부분검증, 대상0개 분리, partial/null/bool/빈값/대문자SHA/container 손상/hash0, canonical상충/hash0, 파일누락 구분, 정확/부족 예산 및 타입, partial 상태의 실제 불일치, pin/strictJSON/원격/root이탈/nonfile, 공유 파일·manifest 변경, logicalretarget·누락파일 출현, CP949·UTF8·새출력 보호를 검사했다. 실제 보조2,855파일은 구현/독립 담당이 읽지 않았으며 root만 한 번 실행한다. 독립시험 수는 전체 회귀에 중복 합산하지 않는다.

## UI와 인계

공개 API/화면 상태 계약 없는 내부 CLI라 UI 수정·실행 중 frontend 반영·브라우저 검증은 필요하지 않다. 후속 UI 연결은 web_ui에 확정 API·상태·오류와 실제 근거를 전달해야 한다. root는 실제 보조자산 streaming1회·원본/원장/기존 계약 보호·전체 회귀·인계서를 담당하고 이해 에이전트에 완료 코드/시험/부분 커버리지·미검증 범위를 전달한다. byte 검증을 의미·과학성능·운영 승인으로 표현하지 않는다.

## Root 실제 실행 결과 — 부분 커버리지

**VERIFIED_REAL(명시된 파일의 바이트 SHA 한정):** Root의 CP949 CLI가 종료0으로 완료했다. [실제 JSON](../../evidence/integration/recovery-auxiliary-content-live-final-20261017.json), [CLI 로그](../../evidence/integration/recovery-auxiliary-content-cli-final-20261017.log). 고유2855파일 모두 MATCH, 계획=실제읽기12719583B<=67108864B, issue0이다. `content_validation=RECORDED_AVAILABLE_SHA_MATCH_PARTIAL`, `coverage_status=INCOMPLETE_REFERENCES`, source_quality/boundary의 UNKNOWN은 각80행/합160역할참조다. 고유 파일 수1384/1384/86/1과 명시참조 행수1384/1384/1304/1304를 구분한다. 같은파일의 반복참조는1회해시했다.

동일digest의 다른경로그룹175개/그룹내619경로/최대12경로다. 역할집합별 patch_quality147그룹, patch_label+patch_quality9그룹, source_quality4그룹, patch_label15그룹이다. 이는 명시기대SHA가 일치한 byte 동일성 진단이다. 장면·공간 중복/누출·라벨의미·quality 적합성을 판정하지 않고 삭제/분할재배정하지 않는다. 이전 image1475와이번명시aux2855의합4330은 과거readiness의4335파일전체를 새로감사했다는 뜻이 아니다. 미기재원본quality5파일의기대SHA를 추정하지 않았다.

실제streaming은Root만1회, 구현/독립담당은합성시험만수행했다. 라벨/quality의 raster 헤더·정합·범주값 의미, boundary 구조/공식승인, 독립 기하·과학성능은 별도 후속이다. 모든실행/정산/재개/학습승인false·BLOCKED/환불0 유지.

## Root 회귀·보존과 다음 단위

관련14PASS3.996초/독립14PASS3.534초이며 독립시험은 전체에 중복 합산하지 않는다. [전체 회귀 로그](../../evidence/integration/recovery-auxiliary-content-full-tests-20261017.log)는 **432건/431PASS/1SKIP/103.139초/종료0**이다. SKIP은 기존 OSsymlink 생성 권한이며 deterministic 경계시험은 PASS다. [보존 증거](../../evidence/integration/recovery-auxiliary-content-live-integrity-20261017.json)는 보호132참조SHA·존재, 기존계약11SHA, 이전추적코드/데이터/계약 변경0, 보조2855파일stat/prefix16·1471부모폴더목록 변화0을 기록한다. 이것을 원자적 snapshot 보장으로 해석하지 않는다.

후속은 명시된 label/quality raster의 로컬 GTiff 헤더·원본/patch 영상과의 크기/CRS/affine·단일band 계약을 코드에 근거하여 대조하는 작은 읽기 단위다. 레거시 누락은 계속 UNKNOWN이며 dtype/nodata의 허용조건은 실제 materialize/readiness 계약을 먼저 확인한다. 픽셀 범주값 의미/quality 적합성·boundary 구조/기관승인/독립기하·정산·실자료학습은 별개다. 현재 BLOCKED와5ML차단·terminal없는2건/예약136314880B는 유지한다.

## 후속 헤더·정합 검사

[문서51](51_recovery_auxiliary_headers_validation.md)은 명시label/quality와짝영상의안전GTiff헤더·크기/CRS/affine·생성count/dtype/nodata계약을읽기대조한다. 현재파일전체SHA를다시검사하지않으므로본문의SHA증거와별개관측이며,픽셀의미/QA적합·boundary구조/공식승인·전체readiness를증명하지않는다.
