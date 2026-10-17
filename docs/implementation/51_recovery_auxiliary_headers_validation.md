# 보조 GTiff 헤더·짝영상 격자 대조 — 2026-10-17

## 상태와 목적

**TESTED_SYNTHETIC:** 작은 GTiff fixture만 사용하는14개 시험을 통과했다. **VERIFIED_REAL(계획 메타데이터):** 고정 manifest의 명시 auxiliary TIFF는 patch label1,384/patch quality1,384/source quality86=2,854개이고 paired source/patch image1,475개를 합쳐 고유4,329헤더가 예상된다. source-quality의 양키가 없는 레거시80행은 UNKNOWN이다. 실제 전체 헤더 관측·보존 결과는 root가 별도 확정한다. **BLOCKED:** 라벨 의미·픽셀 QA·과학성능·기관 경계승인·정산/재개는 미검증이다.

[문서50](50_recovery_auxiliary_content_validation.md)의 보조 byte SHA와 별도인 이번 companion은 label/quality GTiff의 실제 헤더와 paired image 격자만 대조한다. boundary는 OUT_OF_SCOPE다. manifest SHA만 현재 pin하며 과거 raster 내용 SHA 증거를 이번 실행에서 다시 검증했다고 표현하지 않는다. 기존 코어·collector·원장·lock·분할·모델·데이터는 수정하지 않는다.

## 실제 생성 계약과 readiness의 차이

[collect_samples.py](../../scripts/collect_samples.py)의 quality writer는 count1/uint8/nodata0이며 label writer도 count1/uint8/nodata0이다. [collect_training_grid.py](../../scripts/collect_training_grid.py)의 `materialize_patches`는 label의 원래 uint8 배열과 quality의 `valid.astype(uint8)`을 각각1band·nodata0, image profile의256×256/CRS/window transform으로 저장한다. source-quality는 source image profile의 원래 크기/CRS/affine과 정렬되어야 한다.

따라서 이번 검사에서는 세 auxiliary 역할 모두 실제 관측한 count1/dtype uint8/nodata0를 요구한다. dtype에서 nodata를 추론하지 않는다. 기존 header helper는 nodata를 반환하지 않으므로 [새 모듈](../../backend/app/data/recovery_auxiliary_headers.py)의 안전 reader가 GTiff를 한 번 열어 nodatavals를 직접 관측한다. paired image는 여러 band·float32일 수 있으므로 auxiliary와 image count/dtype가 같아야 한다고 요구하지 않는다.

[readiness](../../backend/app/ml/readiness.py)는 [raster assert_aligned](../../backend/app/ml/raster.py)의 exact transform 검사뿐 아니라 픽셀·시기·라벨 provenance·품질·클래스 대표성 등 전체 조건을 평가한다. 이번 헤더 tolerance 대조는 readiness 통과 증명이 아니다. `readiness_full_gate_revalidated=false`를 유지한다.

## 계획·역할·커버리지

`inspect_recovery_auxiliary_headers(data_root, expected_manifest_sha256, max_unique_headers=10000)`는 고정 aggregate 경로를 caller의 명시 소문자64자리 SHA로 pin하고 strict JSON을 읽는다. 검사 역할은 patch_label/patch_quality/source_quality이며 paired patch_image/source_image도 경로와 기대SHA를 전수 계획한다. 기대SHA는 형식·canonical path 상충만 검사하며 바이트 해시는 계산하지 않는다.

- source-quality path/SHA가 양쪽 모두 미기재면 UNKNOWN_REFERENCE_ABSENT로 기록하고 known patch검사를 계속한다. 한쪽만 있거나 명시null/잘못된path/SHA는 plan INVALID다.
- patch label/quality와 paired image 참조는 필요하므로 누락도 plan INVALID다. 필드를 다른 행이나 기본경로로 추정하지 않는다.
- 모든 명시 canonical 경로의 SHA 형식·상충·파일 존재와 일반 파일 여부를 확인한 뒤에만 헤더 읽기를 시작한다. malformed/conflicting/missing 계획은 헤더0개로 거부한다.
- unique header 예산은 정확한 정수1..10000이며 기본10000이다. 동일 파일의 반복행/역할은 한번만 열고, 고유 파일이 예산을 초과하면 헤더0개로 실패한다.
- boundary 참조는 값·형식·경로를 읽기 대조하지 않는 OUT_OF_SCOPE다. 이번 결과를 boundary 구조나 권한 검사로 해석하지 않는다.

role_coverage의 recorded_rows/unknown_rows/matched_rows/exact_affine_rows와 unique_files를 구별한다. 모든 known 헤더가 맞아도 legacy80행이 있으면 KNOWN_HEADERS_MATCH_PARTIAL/INCOMPLETE_REFERENCES다. 빈/손상 계획을 match로 표시하지 않는다. source-quality가 UNKNOWN이어도 명시 paired source image 헤더 자체의 invalid를 무시하지 않는다.

## 로컬 GTiff 헤더 읽기와 정렬

원격/UNC/VSI/root 이탈을 거부하고 일반 로컬 파일만 연다. 첫8바이트의 Classic/BigTIFF 양 endian signature를 검사하고 VRT/XML 등은 GDAL open 전에 거부한다. `rasterio.open(mode='r', driver='GTiff', GEOREF_SOURCES='INTERNAL')` 뒤 실제 driver도 GTiff인지 검사한다.

기존 [header 안전 helper](../../backend/app/data/recovery_raster_headers.py)의 SAFE_GDAL_OPTIONS·stat·finite/nonsingular affine 검사·tolerance를 변경 없이 재사용한다. PAM=NO, READDIR=EMPTY_DIR, PROJ_NETWORK=OFF, INTERNAL georef, VRT Python=NO로 local internal metadata만 읽고 sidecar override/쓰기를 사용하지 않는다. dataset.read/read_masks/통계/tags 또는 raster 전체 read_bytes/SHA를 호출하지 않는다.

헤더 width/height/count는 양수·CRS 존재·affine finite/nonsingular여야 한다. 각 auxiliary는 paired image와 width/height 및 CRS가 같고, patch 역할은256×256이어야 한다. count1/dtype uint8/nodata0는 actual header에서 확인한다.

6계수 affine 대조의 허용오차는 기존과 같은 absolute1e-7/relative1e-12이다. 각 check의 `affine_exact_match`와 역할별 exact_affine_rows는 별도로 기록한다. 허용오차 안의 차이는 HEADER_ALIGNMENT_MATCH여도 exact_affine_match=false다. 이것을 readiness의 exact alignment가 확인된 것으로 표현하지 않는다.

계획 stat(size/mtime/ctime/inode/device), 읽기 전후와 종료 stat, 논리 경로→resolved target, manifest SHA를 재확인한다. 누락 파일 출현·기존 파일 변경·alias retarget은 거부한다. cache는 고유 경로당 헤더 한 번이며 원본 prefix/전체bytes·sidecar 목록 보존은 합성 fixture에서 검사한다. 다중 파일의 원자 snapshot·전체 raster 내용 보존 SHA는 이번 기능이 제공하지 않는다.

## 상태와 한계

항상 status=BLOCKED, exactly_once_applied=UNKNOWN, ready_for_training/training_executed/scientific_accuracy_validated/settlement/execution/automatic_resume=false, 환불0·네트워크0·원본쓰기0이다. pixel_arrays_read/raster_content_sha_revalidated/label_semantics_validated/quality_suitability_validated/boundary_authorization_verified도 false다. recorded_sha_status=FORMAT_AND_CONFLICT_ONLY다.

quality 헤더 정렬은 실제 구름/마스크 값의 적합성 검사가 아니고 label 헤더는 클래스 의미·출처·정답성 검사가 아니다. 같은 CRS/격자·SHA형식도 독립 공간누출/과학성능·운영 승인을 뜻하지 않는다. 원장/ref 양방향·crop·byte 검증 등 기존 companion의 결과를 현재 다시 실행했다고 표현하지 않는다.

## CLI·시험·인계

[inspect_recovery_auxiliary_headers.py](../../scripts/inspect_recovery_auxiliary_headers.py)는 stdout/stderr CP949 ASCII escape, 파일 UTF-8이다. 새 evidence 경로만 허용하며 기존/evidence 밖/data root 아래 출력은 헤더 검사 전에 거부한다.

```powershell
python scripts/inspect_recovery_auxiliary_headers.py --data-root data `
  --expected-manifest-sha256 cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f `
  --max-unique-headers 10000 `
  --output evidence/integration/recovery-auxiliary-headers-live-20261017.json

$env:PYTHONPATH="$PWD\.runtime;$PWD\backend"
python -m unittest discover -s tests -p test_recovery_auxiliary_headers.py -v
```

exit0은 BLOCKED 진단 보고서 생성이며 malformed/global pin·경로·예산·stale 실패는 exit1이다. 개별 헤더 문제/부분 커버리지는 issues가 있는 보고서로 반환될 수 있다.

[시험](../../tests/test_recovery_auxiliary_headers.py), [관련 로그](../../evidence/integration/recovery-auxiliary-headers-tests-20261017.log): **14 PASS, 5.580초**. actual nodata/count/dtype·차원/CRS/affine·회전skew·tolerance vs exact, source-quality 원래크기, legacy UNKNOWN, malformed/상충/누락/예산 header0, paired image 오류, 캐시/안전Env/rmode/픽셀·전체SHA trap, bytes·sidecar목록 불변, VRT/BigTIFF/invalid CRS/singular/nonfinite, strictJSON/pin/root이탈, stat/manifest/alias/missing출현, CP949/새출력 보호를 검사했다. 독립시험 수는 전체 회귀에 중복 합산하지 않는다. 실제4,329헤더는 구현/독립 담당이 열지 않고 root만 실행한다.

공개 API/화면 상태 계약 없는 내부 CLI이므로 UI 코드 수정·실행 중 frontend 반영·브라우저 검증은 필요하지 않다. 후속 화면 연결은 web_ui에 확정 API·상태·오류와 실제 근거를 전달해야 한다. root는 실제 실행·보호대조·전체 회귀·원장/인계서를 기록하고 이해 에이전트에 완료 코드·시험·부분 커버리지·미검증 범위를 전달한다.

## Root 실제 결과·전체 회귀·보존

**VERIFIED_REAL(명시된 GTiff 헤더·짝영상 정합 한정):** Root CP949 CLI 종료0, [실제 JSON](../../evidence/integration/recovery-auxiliary-headers-live-final-20261017.json), [CLI 로그](../../evidence/integration/recovery-auxiliary-headers-cli-final-20261017.log). 고유4329개 모두 VALID_HEADER, 짝비교4072개 모두 HEADER_ALIGNMENT_MATCH·affine_exact_match=true다. patch_label1384/patch_quality1384/source_quality1304참조행의 모든 count1·uint8·nodata0/크기/CRS/affine 계약이 일치했다. sourcequality고유86파일은1304행이 공유한다. sourcequality80행은 UNKNOWN이며 `KNOWN_HEADERS_MATCH_PARTIAL/INCOMPLETE_REFERENCES`, issue0/boundary OUT_OF_SCOPE다.

일치한4072 affine가현재자료에서정확일치했다는것과검사기의허용오차계약(abs1e-7/rel1e-12)은구분한다. `readiness_full_gate_revalidated=false`, 현재내용SHA재검증false·픽셀readfalse를유지한다. 원자snapshot·독립기하·라벨의미/QA적합·성능/기관승인은증명하지않는다. 실제헤더는Root만1회검사했고구현/독립담당은작은합성GTiff만사용했다.

관련14PASS5.580초·독립14PASS9.720초이며 독립시험을 전체에 중복합산하지 않는다. [전체 회귀](../../evidence/integration/recovery-auxiliary-headers-full-tests-20261017.log)는 **446건/445PASS/1SKIP/116.342초/종료0**다. SKIP은기존OSsymlink권한/deterministic경계시험PASS. [보존 증거](../../evidence/integration/recovery-auxiliary-headers-live-integrity-20261017.json): 보호132참조SHA·존재/기존계약12SHA불변·이전추적코드/데이터/계약변경0·4329stat/prefix16와1475부모목록변화0. 이는전체raster내용SHA나원자snapshot증거가아니다.

다음작은대기열은명시boundary JSON구조·참조출처진단이다. 실제소비코드의FeatureCollection/지역식별계약을먼저읽고고정manifest/명시SHA·크기/중복JSON키/비유한좌표·경로를제한한다. legacy80행의경계참조는추측하지않는다. 구조타당성이공식ADM1경계/승인/행정권한·기하독립성을보장하지않는다. 현재단위에서경계구조검사/픽셀값해석/정산/학습을수행하지않았다. BLOCKED/5ML차단·terminal없는2건·예약136314880B보존/환불0유지.

## 후속 경계 구조 진단

[문서52](52_recovery_boundary_validation.md)는 명시 boundary JSON의 고정SHA·제한된구조·지역식별 연결을 별도로 검사한다. 본헤더검사에서는boundary OUT_OF_SCOPE이며, 후속구조결과도공식ADM1/위상/기관승인·픽셀포함검사로확대하지않는다.
