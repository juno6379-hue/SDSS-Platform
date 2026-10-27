# Unit358 G6/G11 secondary fail-closed 교정

## 쉬운 설명과 상태

기존 secondary manager는 실제 모델을 실행하지 않고 WorldCover 값을 prediction으로 복제하고, 난수 confidence와 거의 전유효 mask를 새 GeoTIFF로 만들었다. 또한 GeoServer를 조회하지 않고 모든 레이어를 `PUBLISHED_ONLINE`으로 기록하고, 고정 경험률로 변화·탄소·파편화 통계를 계산했다.

이 경로를 제거했다. 현재 기본 경로는 파일과 통계를 만들지 않으며 증거가 없으면 null과 `BLOCKED`를 반환한다.

| 범위 | 상태 |
|---|---|
| 합성 prediction/confidence/mask 생성 제거 | `TESTED_SYNTHETIC` |
| secondary evidence manifest·SHA·grid·값 계약 검사 | `TESTED_SYNTHETIC` |
| WorldCover와 동일 prediction 차단 | `TESTED_SYNTHETIC` |
| named-layer 열거와 로컬 파일 상태 분리 | `TESTED_SYNTHETIC` |
| 실제 모델 추론·secondary 파일 검증 | `BLOCKED` |
| 실제 GeoServer 전수 게시·GetMap/픽셀 대조 | `BLOCKED` |
| 실제 T1/T2 변화·면적·탄소·파편화 통계 | `BLOCKED` |

## 코드와 데이터 계약

`GeoServerSecondaryAndChangeManager` 생성자는 directory를 만들지 않는다. `materialize_secondary_layers()`는 호환 이름만 유지하며 실제로는 읽기 전용 evidence inspection을 수행한다.

manifest가 없거나 잘못되면 18개 기대 record가 다음 상태로 반환된다.

```json
{
  "evidence_status": "BLOCKED",
  "model_prediction": false,
  "file_rel_path": null,
  "file_sha256": null,
  "published_status": null,
  "wms_getmap_url": null
}
```

실제 artifact 판정에 필요한 manifest 상위 계약은 다음과 같다.

- `schema_version=1.0`
- `evidence_status=VERIFIED_REAL`
- `source_type=EXECUTED_MODEL_INFERENCE`
- checkpoint/input asset SHA-256
- data root 안의 checkpoint/input asset 상대경로와 실제 파일 SHA 일치
- `confidence_source=MODEL_SOFTMAX_MAX_PROBABILITY`
- `valid_mask_source=INFERENCE_INPUT_VALID_MASK`
- 주별 연도와 prediction/confidence/valid-mask 경로·SHA

검사기는 경로가 data root 밖으로 나가지 못하게 하고, 세 raster의 CRS/affine/bounds/shape를 정확히 비교한다. valid mask는 `{0,1,255}`, 유효 prediction은 0~8, confidence는 0~100이어야 한다. 동일 주·연도의 WorldCover reference와 prediction SHA 또는 pixel 배열이 같으면 `PREDICTION_EQUALS_REFERENCE_LABEL`로 세 record를 모두 차단한다.

게시 상태는 data root 안의 GetCapabilities XML 원문 경로, 실제 원문 SHA-256, 원문에서 파싱한 정확한 named-layer 3종 열거가 함께 있을 때만 `VERIFIED_NAMED_LAYER_ENUMERATION`이다. manifest에 문자열 목록만 적는 것으로는 게시 상태를 만들 수 없다. 로컬 파일 확인만으로 WMS URL이나 GetMap 성공을 만들지 않는다.

`compute_annual_changes()`는 실제 T1/T2 계약이 아직 구현되지 않았으므로 6개 주의 총 토지면적 식별값 외 모든 측정값을 null로 반환한다. 상태는 `BLOCKED_NO_VERIFIED_T1_T2_MODEL_PREDICTIONS`다.

## 산출물 사용법

```python
manager = GeoServerSecondaryAndChangeManager(
    data_root,
    evidence_manifest=approved_inference_evidence,
)
records = manager.materialize_secondary_layers()  # read-only inspection
changes = manager.compute_annual_changes()         # currently BLOCKED/null
```

`export_all_downstream_deliverables()`는 지정한 로컬 output directory에 fail-closed 보고서만 새로 쓴다. 기존 CSV에 append하지 않으며 GeoServer, 운영 registry, 원격 서비스에는 쓰지 않는다.

## 기존 04/08 자료 교정

- primary manifest와 registry 54행의 `PUBLISHED_ONLINE`을 `UNVERIFIED_NOT_ENUMERATED`로 교정하고 WMS URL을 제거했다.
- 실제 로컬 TIFF 54개의 SHA-256을 기록했다.
- coverage comparison/newly recovered/still missing 18개를 `TESTED_SYNTHETIC`으로 표시했다.
- 나머지 36개는 파일 SHA만 확인했으며 원천 provenance는 미검증이다.
- 기존 60개 전수 등록, 100% 픽셀 일치, secondary confidence 실측 주장을 철회했다.

## 시험 근거

집중 시험은 다음을 확인한다.

- manifest 없는 기본 경로에서 파일/directory 생성 0
- 18개 record 전부 BLOCKED/null
- 로컬 artifact와 named-layer publication 상태 분리
- capabilities SHA와 exact layer enumeration 동시 요구
- checkpoint/input 경로와 실제 SHA, Capabilities XML 원문과 실제 SHA 요구
- manifest의 named-layer 자기주장만으로 게시 상태가 되지 않음
- WorldCover 복제 prediction 차단
- 변화·탄소 통계 null
- export의 append 및 `PUBLISHED_ONLINE` 재생성 차단

```text
python -m pytest tests/test_geoserver_secondary_fail_closed.py -q
8 passed, 15 warnings

python -m pytest tests/test_geoserver_primary_layers.py tests/test_geoserver_secondary_fail_closed.py tests/test_landcover_tiles.py -q
31 passed, 137 warnings, 20.32s
```

경고는 rasterio affine pending-deprecation이다. 실제 추론, 원격 요청, GeoServer 쓰기, 운영 registry 쓰기는 0건이다.

## 남은 차단

실제 모델 checkpoint로 6개 주 T1/T2 inference를 실행하고, 입력/출력 SHA와 valid mask를 고정한 뒤에야 변화 측정 구현을 시작할 수 있다. 이후에도 named-layer capabilities 원문, GetMap, 원본 픽셀 대조를 별도 증거로 보존해야 한다. 현재 데이터 split은 scene conflict와 class/contribution gate 때문에 `learning_ready=false`이므로 재학습·승격·배포 승인으로 확대할 수 없다.
