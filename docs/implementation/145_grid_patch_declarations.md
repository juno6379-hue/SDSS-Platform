# 145 — 새 patch 영상 description과 training support mask의 구분

상태: **TESTED_SYNTHETIC**. `scripts/collect_training_grid.py`의 `materialize_patches`에만 작은 metadata 보강을 했다. 새 patch image.tif에는 원본 영상의 band description을 있는 값만 그대로 기록하고, patch row에는 scene 품질 mask의 선언을 잘못 상속하지 않도록 구분한다. 신규 집중 시험과 이 문서를 추가하며 기존 수집·소비·Registry·main/API/UI는 바꾸지 않는다. 운영 수집·학습이나 원본 자료 변환은 실행하지 않았다.

## 영상 description의 원형 전파

기존 image/label/quality 쓰기 루프에서 **name == image일 때만** 원본 `image.descriptions`를 index 순서대로 읽는다. None이 아닌 값을 같은 band index에 그대로 기록한다. None 위치는 새 파일의 기본 None으로 남고 unknown 이름이나 순서를 임의로 보정하지 않는다. B02/B03/B04/B08/B11/B12를 새로 발명하거나 label/quality의 한 밴드에 영상 이름을 복사하지 않는다.

픽셀 배열·count·dtype·nodata=0·CRS·window affine·파일 이름은 그대로다. 영상 description이 추가되므로 새 image 파일 SHA는 baseline과 달라질 수 있으며, 같은 Registry 버전을 자동 수정하거나 이전 SHA를 재사용하지 않는다. description은 명시 metadata의 전파이지 분광/물리 보정·모델 호환·기관 품질 인증이 아니다. 원본의 description이 없거나 순서가 다르면 새 patch도 그대로여서 기존 strict header gate가 차단하는 것이 정상이다.

## scene 품질과 결합 지원 mask는 다르다

144의 scene quality_mask_semantics는 SCL 및 finite/nonzero 영상 조건에 대한 binary_validity 선언이다. 기존 patch의 quality.tif는 이미 다음 교집합을 기록했다.

```python
valid = (scene_quality == 1) & inside_aoi & (labels != 0) & finite_nonzero_image
```

따라서 label 부재나 AOI 밖의 픽셀까지 0이 되는 patch quality를 순수 scene 품질과 같은 의미라고 선언할 수 없다. 원래 `copy.deepcopy(source)`가 새 scene 선언을 patch 최상위에 그대로 남기는 문제를 막기 위해, **quality_mask_semantics만 제거**하고 다음 별도 필드를 넣는다.

```json
{"training_support_mask_semantics":{"schema_version":1,"kind":"training_support","valid_value":1,"invalid_value":0}}
```

이 exact4는 새 내부 row 선언이며 GMAIS 공식 mask 계약이나 기관 정책이 아니다. 0/1 배열이라는 사실만으로 pure image QA를 증명하지 않는다. 이 선언을 source.mask_semantics의 binary_validity로 자동 복사하거나 이름을 바꿔 Registry·품질 보고서에 넣지 않는다. 실제 consumer는 명시된 kind와 intrinsic nodata를 별도로 확인해야 한다.

기존 결합 mask의 nodata=0·valid 계산·label zeroing·품질 threshold·AOI fraction·split·class count를 바꾸지 않는다. 순수 mask처럼 보이게 하려고 nodata=None으로 바꾸지 않는다. source_window에 새 scene semantics 키를 추가하지 않으며 기존 원본 경로·SHA 이력은 그대로다. 원본 report와 scene row의 quality_mask_semantics는 수정하지 않고 보존한다. 새 patch row에서 별도 training_support_mask_semantics만 기록한다.

## 기존 동작과 안전 범위

변경은 materialize_patches의 **6줄 삽입·기존 줄 삭제 0**이며 원래 LF 형식을 유지했다. 기존 원본 영상·scene quality·라벨·보고서 파일을 다시 쓰지 않고, materialize 호출의 입력 report 객체도 바꾸지 않는다. 예산·원장·예약·다운로드·split·샘플/라벨 정책이나 raw source crop은 수정하지 않는다.

다만 기존 materialize_patches는 mkdir(exist_ok=True)와 rasterio.open(..., 'w')를 사용한다. 이번에 이를 EXCL writer로 바꾼 것이 아니므로 **수동 재호출이 이미 있는 patch 경로를 덮어쓰지 못한다고 주장하지 않는다**. 이번 시험은 Temp 출력 디렉터리만 사용했고 운영 경로를 호출하지 않았다. 향후 호출자가 새 출력 경로와 버전 의도를 별도로 관리해야 한다. 기존 운영 patch나 미정의 description을 자동 역채움하는 기능도 없다.

## 실제 Temp 시험

최종 집중은 **6 PASS / 2.778초 / exit 0**, `evidence/integration/grid-patch-declarations-agent-20261018.log`다. 명령은 project root에서 `PYTHONPATH=.runtime;.;backend;tests`와 `python -m unittest test_grid_patch_declarations -v`를 사용했다. 실제 Temp GTiff만 읽고 썼고 경계 SHA 경로도 Temp fixture로 분리했다. 실제 네트워크·운영 자료·Store/학습 실행은 없다.

- 512×256 원본을 256×256 두 patch로 나눠 description과 원순서, image 배열·nodata·label/quality description None, window 비중복·split을 확인했다.
- 원본 전체 None, 일부 None, unknown 및 reordered 이름을 그대로 전파하고 원본 scene 선언과 report 객체를 보존했다.
- pinned Git a3f4a94a의 원문을 격리 모듈로 실행한 별도 Temp 출력과 비교했다. label/quality 파일은 **바이트와 SHA까지 동일**, image는 배열/profile이 동일하고 description 및 해당 SHA만 달라졌다. class count·valid/AOI fraction·source group·위치·분할 metadata도 변경 범위를 제외하면 같았다.
- 실제 129 `_header`가 올바른 새 영상은 수용하고 description이 없는 영상은 거부함을 확인했다. 실제 mask header를 133 `_binary_counts`에 전달하면 유지된 nodata=0 때문에 MASK_INTRINSIC_VALIDITY_UNSUPPORTED로 거부된다. 139 선언 준비도 training_support를 binary_validity로 수용하지 않는다. 이는 해당 native/순수 경계의 직접 시험이며 **전체 Registry·133 통합 등록 시험이라고 표현하지 않는다**.
- 300×260 입력의 256 밖 remainder를 새로 쓰지 않는 기존 정책과 label_path 없는 scene skip을 유지했다.

초기 집중 **6 PASS / 3.213초**는 `grid-patch-declarations-agent-initial-20261018.log`로 보존했다. 이후 mask 경계 시험에 실제 header를 넣고 정확한 intrinsic-validity 오류 code를 확인하도록 강화해 최종 시험을 실행했다. 제품 source는 그 강화 때문에 바꾸지 않았고 초기·최종을 합산하지 않는다.

동결 source SHA는 `d312660f1a25fb6a9477f101e09aacd14f543636614726fb13092f42bceda3d6`, test SHA는 `f183ba9e6469e5fff225d2ebd163fea2c54bcadf3f6bc604f53046aa2af38805`다. Root는 관련/전체 회귀·원본 보존·공통 인계/Git과 이해 에이전트 배정을 맡는다. 이해 담당은 완료된 코드·Temp 파일과 시험 증거를 읽고 해설·발표 대본·FAQ·INDEX·변경 이력을 갱신한다.

독립 최종 `grid-patch-declarations-independent-20261018.py/.json/.log`는 **7 PASS / 0 SKIP / 실패·오류 0 / 4.2726165초 / exit 0**다. source/test 동결 SHA가 일치하고 baseline a3f4a94a의 기존 7개 소스가 Git·전후 바이트에서 같으며 materialize_patches 외 AST도 동일했다. 실제 Temp 원본 파일과 입력 report 보존, None/unknown/permutation·label/quality description None·nodata0, baseline 대비 image 배열/profile·label/quality bytes·split/class count/valid/AOI row 동등을 확인했다. scene 선언 제거와 별도 training_support 사본을 검증했다. 129의 RASTER_BAND_SIGNATURE_INVALID 및 133의 MASK_INTRINSIC_VALIDITY_UNSUPPORTED는 실제 native 경계에서 관측했고 Store·전체 Registry 소비 호출은 0이다. 운영·네트워크·학습·추론은 실행하지 않았으며 집중·관련·독립 묶음을 합산하지 않는다.

Root의 source-scope 검증은 **baseline에 지정한 두 metadata 편집을 정확히 재적용하면 최종 source와 같고** 다른 AST 및 LF가 유지됨을 확인했다. 07:17:15 보존 감사에서는 **tracked source 431개 중 승인한 grid 1개 변경·나머지 430개 불변**, 보호 파일 141개·이전 증거 1399개·catalog 14행 SHA·운영 dataset_versions 0·예약 136314880바이트 유지를 확인했다. 이 tracked source 집계는 이전 snapshot 파일 개수나 자동시험 개수와 다른 범위다. 전체 회귀 후 최종 감사와 구분해 기록한다.

Root 관련 15개 모듈은 **171 실행 / 170 PASS / 1 SKIP / 79.284초 / exit 0**, `grid-patch-declarations-root-related-20261018.log`다. SKIP은 기존 test_collection_recovery의 실제 symlink가 data root 밖을 읽지 못하는지 확인하는 시험으로 Windows 생성 권한이 없어 제외됐다. 관련 회귀와 독립·집중 시험 수를 합산하지 않는다.

기존 producer를 수정했으므로 이번에는 Root가 전체 backend 회귀도 실제 실행했다. 최종은 **1432 실행 / 1431 PASS / 1 SKIP / 332.720초 / exit 0**, `grid-patch-declarations-full-20261018.log`다. 같은 기존 Windows symlink 권한 시험 한 건을 제외했고 첫 전체 실행에서 통과해 실패 후 전체 재실행은 없었다. 이전 전체 회귀 결과를 재사용한 수치가 아니며 집중·관련·독립과 합산하지 않는다.

전체 회귀 뒤 07:23:48의 `grid-patch-declarations-live-integrity-final-20261018.json`에서 **tracked source 431개 = 승인한 grid 1개 변경 + 불변 430개**, 보호 파일 141개·이전 증거 1399개·catalog 14행 canonical SHA·운영 dataset_versions 0·예약 136314880바이트 유지가 다시 확인됐다. 07:23:50의 넓은 프로세스 패턴 조회에서도 실제 collector/train은 없었다. ACTIVE/10분 보고 예약과 API 등 기존 프로세스를 실제 수집·학습 실행으로 표현하지 않는다. 원본 source/report/배열 보존과 metadata에 따라 새 image SHA가 달라지는 범위를 구분한다.

기존 main/HTTP/137 계약·UI·모델 metadata를 바꾸지 않으므로 이번 frontend/build/browser 재실행은 필요하지 않다. 새 description과 training_support 선언은 실제 운영 수집 재개·연차 자료 확보·라벨 독립성·기관 QA/모델/실행 승인을 뜻하지 않는다. 원본·원장·lock·예약·분할·모델을 보존하며, 실제 운영 프로세스에 새 코드가 적용됐다는 검증도 별도다.
