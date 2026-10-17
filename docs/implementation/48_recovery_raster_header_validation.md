# 로컬 GTiff 헤더·crop bounds·patch 격자 대조 — 2026-10-17

## 상태와 목적

**TESTED_SYNTHETIC:** 작은 원본512×512와2×2의256×256 patch를 직접 만든 격리 GTiff fixture를 포함한17개 시험을 통과했다. **VERIFIED_REAL:** 실제 원본 이미지91개·active patch1,384개(고유 경로 예상1,475개)의 최종 헤더 조사 결과·보존 근거는 root가 별도 기록한다. **BLOCKED:** 픽셀/라벨/품질·내용 SHA·독립 공간 누출·과학적 성능·정산/재개는 미검증이다.

새 companion은 [문서47](47_recovery_crop_reconciliation.md)의 JSON crop 좌표를 실제 로컬 GTiff의 크기·CRS·affine 헤더와 대조한다. 기존 crop/aggregate/terminal/recovery/collector·모델·데이터·원장·lock을 수정하지 않는다. 원장/출처/연도·지역 검사를 다시 실행하는 기능도 아니다. 입력 행과 원본 파일을 보존한다.

## 구현과 로컬 입력 경계

[recovery_raster_headers.py](../../backend/app/data/recovery_raster_headers.py)의 `inspect_recovery_raster_headers(data_root)`는 고정 aggregate JSON에서 active scenes의 source_window.path와 image_path만 읽는다. aggregate JSON은 strict 중복 키·비유한 수·형식 검사를 거치고 SHA를 전후 비교한다. label_path/quality_mask_path는 열지 않는다.

raster 경로는 data root 안의 일반 로컬 파일만 허용하며 원격/UNC/VSI/root 이탈·일반 파일이 아닌 경로는 거부한다. 원래 논리 경로→resolved target을 기록하여 조사 중 alias 재지정을 감지한다. GDAL에 넘기기 전 첫8바이트만 읽어 Classic TIFF의 little endian `II*`/big endian `MM*`와 BigTIFF43의 두 endian signature를 검사한다. BigTIFF offset-size8/reserved0도 확인한다. XML VRT/다른 형식은 GDAL open 전에 UNSUPPORTED로 남긴다.

GTiff 헤더는 다음 제한으로만 연다.

- `rasterio.open(path, mode='r', driver='GTiff', GEOREF_SOURCES='INTERNAL')`; 실제 dataset.driver도 GTiff인지 확인한다.
- `GDAL_PAM_ENABLED=NO`, `GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR`, `PROJ_NETWORK=OFF`, `GDAL_GEOREF_SOURCES=INTERNAL`, `GDAL_VRT_ENABLE_PYTHON=NO`를 scoped rasterio.Env로 적용한다.
- CRS/좌표는 TIFF 내부 기록만 사용하고 PAM/worldfile override를 적용하지 않는다. update 모드·PAM 저장·디렉터리 탐색·PROJ 네트워크를 사용하지 않는다.
- dataset.read/read_masks/statistics/stats/tags나 전체 raster SHA를 호출하지 않는다. 픽셀 배열을 읽지 않아도 GDAL은 TIFF directory 및 내부 georeference 메타데이터를 읽는다. 따라서 파일 바이트를 전혀 읽지 않는 검사는 아니다.

## 헤더 및 patch 계약

width/height/count는 양의 정수, CRS는 존재해야 하고 affine6계수는 모두 finite이며 determinant `a*e-b*d`는 finite/nonzero여야 한다. 누락/손상/지원하지 않는 헤더는 MISSING/INVALID/UNSUPPORTED로 표시한다.

[materialize_patches](../../scripts/collect_training_grid.py)는 원본 image profile을 복사하여 width/height256, patch count=image count, dtype=image dtype, transform=image.window_transform(Window(x,y,256,256))으로 쓴다. inspector는 이 계약에 따라 다음을 대조한다.

- crop은 정확한 정수4개 `[x,y,256,256]`이며 boolean/float를 거부한다. x/y>=0,256배수여야 한다.
- x+256<=source.width, y+256<=source.height로 실제 원본 bounds를 검사한다. 무제한 JSON 정수처럼 범위 밖 좌표는 affine float 계산을 건너뛰어 overflow 없이 issue로 반환한다.
- patch width/height는256×256, band count와 band별 dtype은 source와 같아야 한다.
- CRS 객체를 비교하고 affine 전체6계수를 대조한다. 예상 변환은 `sourceAffine @ Affine.translation(x,y)`로, rasterio window_transform과 동일한 일반 affine 계산이다. 회전/skew도 처리하며 north-up을 가정하지 않는다.
- 변환 허용오차는 **absolute1e-7, relative1e-12**이고 `math.isclose`를 계수별 적용한다. 좌표계 단위의 수치 반올림 허용치이며 지리학적 정확도·센서 위치 오차 기준이 아니다.

## 안정성·결과·한계

고유 canonical 경로별 헤더를 캐시하되 매 사용과 조사 종료 시 파일 stat(size/mtime_ns/ctime_ns/inode/device)을 다시 대조한다. 누락 파일 출현도 변경으로 거부한다. 논리 경로 target과 aggregate JSON SHA도 전후 비교한다. raster 전체 SHA를 계산하지 않으므로 stat 변화가 없는 내용 변경까지 증명하는 암호학적 보장은 아니며 여러 파일의 원자적 snapshot/운영체제 lock을 제공하지 않는다.

scene_checks의 HEADER_CONTRACT_MATCH는 해당 원본/patch 헤더 계약의 일치다. 전체 header_consistency=CONSISTENT_HEADERS여도 status는 BLOCKED다. 누락/손상/차이는 issues에 기록하며 개별 문제가 있는 조사도 exit0 보고서를 반환할 수 있다. 안전 경계·stale/global JSON 오류는 exit1이다.

pixel_arrays_read/raster_content_sha_computed/label_quality_checked/same_content_different_file_checked/geometric_independence_checked는 false다. 원본/patch의 recorded SHA가 실제 바이트와 같은지, 다른 파일이 같은 영상인지, 독립 공간 중첩·라벨 품질·모델 정확도를 확인하지 않는다. exactly_once_applied=UNKNOWN, ready_for_training/training_executed/scientific_accuracy_validated/settlement/execution/automatic_resume는 false, 환불0·네트워크0·원본쓰기0을 유지한다.

## CLI와 시험 근거

[inspect_recovery_raster_headers.py](../../scripts/inspect_recovery_raster_headers.py)는 stdout/stderr ASCII escape로 Windows CP949를 지원한다. 출력 파일은 UTF-8이며 프로젝트 evidence 아래의 새 경로만 허용한다. 기존 파일·data root 내부·evidence 밖 출력은 거부한다.

```powershell
python scripts/inspect_recovery_raster_headers.py --data-root data
# 아직 없는 새 경로일 때만 지정
python scripts/inspect_recovery_raster_headers.py --data-root data `
  --output evidence/integration/recovery-raster-headers-live-20261017.json

$env:PYTHONPATH="$PWD\.runtime;$PWD\backend"
python -m unittest discover -s tests -p test_recovery_raster_headers.py -v
```

[시험 파일](../../tests/test_recovery_raster_headers.py), [관련 로그](../../evidence/integration/recovery-raster-headers-tests-20261017.log): **17 PASS, 14.193초**. 실제 GTiff2×2 patch·회전/skew·수치 tolerance·source bounds/grid/types·width/count/dtype/CRS·missing CRS/singular/nonfinite affine·TIFF/BigTIFF 양 endian·VRT 사전 차단·실제 driver guard·GTiff/rmode/internalgeoref/Env 인자·pixel/statistics 메서드 접근 차단·cache·stat/누락 출현·logical retarget·strict JSON·원격/root 이탈·CP949/new evidence/덮어쓰기 보호를 검사했다. synthetic source/patch/기존 PAM/worldfile의 bytes 및 파일 목록 불변도 확인했다.

초기 독립 초안 검토에서 JSON의 매우 큰 정수 crop가 bounds 위반 후 affine float 계산으로 overflow할 가능성을 지적하여 bounds 밖 변환을 건너뛰고 회귀시험을 추가했다. 초기14/15개는 보완/확장 전 이력이다. 독립시험 수는 전체 회귀에 중복 합산하지 않는다.

## UI·다음 인계

내부 CLI만 추가하고 공개 API/화면 상태 계약은 바꾸지 않으므로 UI 코드·실행 중 frontend 반영·브라우저 검증이 필요하지 않다. 후속 화면 노출 시 web_ui에 확정 API·상태·오류와 실제 근거를 인계한다. root는 실제1475개 예상 헤더 조사·stat/샘플/JSON 보호·전체 회귀·원장·인계서를 기록하고 이해 에이전트에 완료 코드·증거·한계를 전달한다. header 관측 보존은 전체 raster SHA 재검증이나 과학적 정확도 승인이 아니다.

## Root 실제 GTiff·전체 회귀 확인

**VERIFIED_REAL(로컬 헤더만):** CP949 환경의 [최종 CLI JSON](../../evidence/integration/recovery-raster-headers-live-final-20261017.json)은 exit0이다. 원본91개+패치1384개=고유GTiff1475개 모두 VALID_HEADER, 1384행 모두 HEADER_CONTRACT_MATCH, issue0/CONSISTENT_HEADERS다. source/patch 크기·CRS·밴드 수·dtype·crop 경계·회전/skew 포함 affine을 검사했다. 명시 tolerance는 absolute1e-7(CRS 좌표 단위), relative1e-12다. 상태는BLOCKED, 픽셀/내용SHA/라벨/quality/독립 기하 검증은false, exactly-once UNKNOWN·정산/재개/학습/과학 승인false를 유지한다.

[시험 후 보호 대조](../../evidence/integration/recovery-raster-headers-live-integrity-20261017.json)는 보호132JSON/원장참조의 SHA·존재 불변, 기존 계약9SHA 불변, 이전 추적 코드/데이터/계약 변경0을 확인한다. raster1475개의 stat+처음16바이트 샘플과 부모1475디렉터리 이름 목록에도 변경이 없다. 이 관측은 전체 raster 파일 바이트의 SHA 증명이 아니다. 합성 GTiff 시험은 입력 전체 bytes와 sidecar 보존도 별도로 확인했다.

관련17 PASS·14.193초, 독립17 PASS·14.125초이며 [전체 회귀](../../evidence/integration/recovery-raster-headers-full-tests-20261017.log)는 **403건/402 PASS/1 SKIP/95.828초/종료0**이다. 독립 실행은 전체403건에 중복 합산하지 않는다. SKIP은 기존 Windows symlink 생성 권한 제한이며 deterministic 경계 시험은PASS다. 공개API/화면 변화가 없어 UI49건/build를 반복하지 않았다. 신규 실자료 수집/학습·정산·환불·재개·배포는 없다. 다음 내용 SHA의 로컬 스트리밍 대조는 별도 PLANNED 단위다.

## 후속 내용 SHA companion

[문서49](49_recovery_raster_content_validation.md)는 이 헤더 검사에서 미검사로 남긴 source/patch image 파일의 전체 바이트 SHA를 caller 고정 manifest의 기대값과 별도로 대조한다. 이 헤더 검사기의 raster_content_sha_computed=false 출력은 그대로이며 새 companion 결과를 함께 읽어야 한다. 새 검사도 픽셀 의미·라벨/quality·기하 독립성·학습/정산 승인을 부여하지 않는다.
