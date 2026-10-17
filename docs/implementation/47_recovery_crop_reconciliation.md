# 연도·지역·crop 좌표 메타데이터 읽기 대조 — 2026-10-17

## 상태와 목적

**TESTED_SYNTHETIC:** 임시 JSON을 이용한 14개 단위시험을 통과했다. **VERIFIED_REAL:** 선행 읽기에서 실제 aggregate 1,384행과 다운로드 source 91행의 year/province가 모두 문자열이며 모든 patch 크기 기록이256×256임을 확인했다. 실제 최종 대조의 수치·보호 SHA는 root의 별도 실행 근거로 확정한다. **BLOCKED:** raster 범위·실제 공간 중첩·과학적 적격성·정산·복구 실행은 미검증이다.

별도 crop companion은 기존 [aggregate 대조](46_recovery_aggregate_reconciliation.md)가 남긴 연도·지역·window_in_source 기록을 비교한다. 기존 코어/API/원장/collector/분할/모델과 데이터를 수정하지 않는다. source 경로와 scene_id의 유일 연결을 다시 구성하지만, 기존 원장/ref 양방향·patch ID/이미지 경로 중복 검사를 재실행하는 기능은 아니다.

## 구현과 실제 계약

[recovery_crop.py](../../backend/app/data/recovery_crop.py)의 `inspect_recovery_crop(data_root)`가 고정 aggregate와 참조 source report JSON을 읽는다. [collect_training_grid.py](../../scripts/collect_training_grid.py)의 `materialize_patches`가 원본 source row를 deepcopy하여 year를 보존하고 province를 batch.province로 지정하며 source_window.path를 원본 image_path로 기록하는 계약을 따른다. aoi는 원래 창 ID에서 province로 바뀌므로 aoi 동일성을 강제하지 않는다.

연도는 [collect_samples.py](../../scripts/collect_samples.py)의 `load_config`가 허용하는2015~2026 범위의 정수 또는 ASCII4자리 문자열이어야 한다. 문자열을 정수로 변환하는 것은 범위 검사뿐이며 입력 행의 타입/값을 정규화하거나 수정하지 않는다. 양쪽 원형 타입과 값이 모두 같아야 EXACT_TYPED_MATCH다. `2023`과 `"2023"`은 MISMATCH, boolean/float/공백/범위 밖 값은 INVALID다.

province는 비어 있지 않은 문자열이어야 하고 공백만 있는 값은 INVALID다. 원형 값을 trim하거나 추정하지 않으며 문자열이 정확히 같아야 한다. report province가 없으면 UNKNOWN이다. source report와 aggregate province의 일치는 부분 문맥 대조이며 batch config의 암호학적 신원이나 행정경계·공식 자료 승인이 아니다.

## crop 검사와 동일성

- window_in_source는 길이4인 `[x,y,width,height]` JSON 배열이어야 한다. 모든 원소는 정확한 정수이며 boolean/float는 거부한다.
- x/y는0이상이고256 grid의 배수여야 한다. width/height는 각각256이어야 한다. 이는 materialize의 `Window(c*256,r*256,256,256)` 계약이다.
- canonical source image 경로+scene_id+crop4좌표가 모두 같은 aggregate 행의 그룹을 DUPLICATE_SOURCE_CROP으로 기록한다. 같은 scene의 서로 다른 crop는 정상이다.
- source report의 downloaded 행을 image_path+scene_id로 색인한다. canonical 같은 report의 중복 참조는 source row 중복으로 세지 않는다. 물리 source row가 여러 개면 AMBIGUOUS_MATCH, 없으면 MISSING_MATCH로 남기며 어떤 행의 year/province도 추측해 대조하지 않는다.
- 유일 연결 뒤 year/province가 누락되면 UNKNOWN, 잘못된 형식이면 INVALID, 원형 타입/값이 다르면 MISMATCH다. 결과는 행별 source_reference와 crop/year/province 상태, issue를 포함한다.

x+256/y+256이 실제 원본 raster width/height 안에 있는지 검사하지 않는다. 다른 경로 파일의 동일 SHA·동일 지리 위치·기하 중첩·crop 물리 중복도 검사하지 않는다. crop 중복0은 데이터 누출0이나 독립 표본 확보를 뜻하지 않는다. 원본 source_window SHA·raster 바이트·변환 좌표·label/quality 동작도 확인하지 않는다.

## 결과와 안전 경계

모순이 없으면 metadata_consistency=CONSISTENT_METADATA지만 status는 항상 BLOCKED다. exactly_once_applied=UNKNOWN, settlement/execution/automatic_resume 권한 false, ready_for_training/training_executed/scientific_accuracy_validated false, 환불0·네트워크0·원본쓰기0을 유지한다.

`crop_coordinate_contract_checked=true`, `year_province_fields_checked=true`는 해당 검사를 시도하는 기능 범위 표시다. malformed/미연결 행이 있어도 전체 성공을 뜻하지 않으므로 행별 상태·issues를 함께 읽어야 한다. raster_bounds_checked/different_file_same_sha_checked/geometric_overlap_checked/source_file_hashes_verified는 false, raster_files_read=0이다.

strict JSON은 duplicate key·NaN/Infinity·overflow 비유한 수·잘못된 컨테이너를 거부한다. 개별 source 오류는 issue로 남기고 global aggregate 형식 오류는 조사 실패다. root 밖/원격/UNC 경로는 열지 않는다. 논리 경로→resolved target과 JSON 파일 SHA·크기·누락 상태를 전후 대조하며 반복 읽기에서 초기 근거를 덮어써 변경을 숨기지 않는다. raster 경로는 resolve만 하고 바이트를 읽지 않는다. 운영체제 lock이나 여러 파일의 원자적 snapshot은 제공하지 않는다.

## CLI와 시험

[inspect_recovery_crop.py](../../scripts/inspect_recovery_crop.py)는 기본 stdout이며 Windows CP949에서도 ASCII escape 출력/오류를 사용한다. `--output`은 프로젝트 evidence 아래의 새 경로만 허용하고 UTF-8로 저장한다. 입력 data root 아래·기존 파일·evidence 밖 출력은 거부한다. 조사 성공의 exit0은 BLOCKED 보고서 생성일 뿐 복구 실행 성공이 아니다.

```powershell
python scripts/inspect_recovery_crop.py --data-root data
# 출력 경로가 아직 없을 때만 지정
python scripts/inspect_recovery_crop.py --data-root data `
  --output evidence/integration/recovery-crop-live-20261017.json

$env:PYTHONPATH="$PWD\.runtime;$PWD\backend"
python -m unittest discover -s tests -p test_recovery_crop.py -v
```

[시험](../../tests/test_recovery_crop.py), [최종 로그](../../evidence/integration/recovery-crop-tests-20261017.log): **14 PASS, 8.084초**. 정상 서로 다른 crop와 원본 bytes 보존/승인false, canonical동일crop, strictint/nonnegative/grid/크기, year/province 타입·값·범위·누락, whitespace province와 원형보존, source누락/모호성, 중복ref dedupe·0patchreport, strictJSON, root이탈·원격, 조사중내용변경·missing출현·logicalretarget, CP949/new evidence·출력 보호를 검사했다.

초기 검토에서 양쪽이 같은 비정상 정수 연도를 유효로 볼 수 있는 공백을 확인해 collector 범위를 적용했고, 공백만 있는 province도 INVALID로 보완했다. 초기12/13시험은 보완 전 이력이며 최종은14개다. 독립검토 결과는 별도 근거이며 전체 회귀에 중복 합산하지 않는다.

## UI 및 다음 인계

새 기능은 공개 API/화면 상태 계약을 바꾸지 않는 내부 CLI이므로 UI 코드 변경·실행 중 화면 반영·브라우저 확인이 필요하지 않다. 후속 화면 노출 시 web_ui에 확정 API·상태·오류와 실제 근거를 전달해야 한다. root는 실자료 최종 실행·보호 SHA·전체 회귀·원장/인계서를 기록하고 이해 에이전트에 완료 코드·로그·범위를 전달한다. raster/공간 검증이나 과학적 승인·정식 학습·정산 재개는 별도 Gate다.

## Root 최종 실제 검사·회귀 확인

**VERIFIED_REAL(로컬 JSON 메타데이터만):** CP949 환경의 [최종 CLI 결과](../../evidence/integration/recovery-crop-live-final-20261017.json)는 exit0으로 확인했다. 출처113개/aggregate1384행이며, source 경로·scene ID의 유일 연결, year/province의 원형 타입·값 일치, crop 정수/256 격자 계약 일치가 각각1384행이다. canonical(source path,scene ID,crop 좌표) 중복0·issue0·CONSISTENT_METADATA지만 status는BLOCKED다. province 일치는 report 문맥에 한하며 batchconfig 인증·행정경계 승인이 아니다. 다른 파일의 동일 영상·실제 raster 경계·픽셀 내용·기하 중첩과 exactly-once는 증명하지 않는다.

[시험 후 보호 대조](../../evidence/integration/recovery-crop-live-integrity-20261017.json)는 누락 상태 포함132참조 불변·기존 계약8SHA 불변·이전 추적 코드/데이터/계약 변경0을 확인한다. 관련14 PASS·8.084초, 독립14 PASS·4.983초이며 [전체 회귀](../../evidence/integration/recovery-crop-full-tests-20261017.log)는 **386건/385 PASS/1 SKIP/111.108초/종료0**이다. 독립 실행은 전체386건에 중복 합산하지 않는다. SKIP은 기존 OS symlink 생성 권한 제한이며 deterministic 경계 시험은PASS다. 내부 CLI라 UI49건/build를 반복하지 않았다. 원본 manifest·원장·lock·분할·모델 보존, 신규 실자료 수집·학습·정산·환불·재개 없음.

## 후속 로컬 GTiff 헤더 companion

[문서48](48_recovery_raster_header_validation.md)은 이 JSON 검사기에서 미검사로 남긴 실제 dimensions/CRS/affine/count/dtype과 crop bounds/patch transform을 로컬 GTiff 헤더로 별도 대조한다. 기존 이 검사기의 raster_bounds_checked=false 등 출력 계약은 보존하며, 새 companion 결과를 함께 읽는다. 새 검사기도 픽셀·내용 SHA·라벨/quality·기하 독립성·학습/정산 승인을 증명하지 않는다.
