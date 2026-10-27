# G11 1차·2차 레이어 픽셀 감사 교정

> 상태: `BLOCKED`
> 교정 단위: Unit358 + Unit361

## 철회한 주장

기존 문서의 `VERIFIED_REAL`, 1차 42개 + 2차 18개 = 60개 전수 등록, 100% 픽셀 일치, confidence 94 실측 주장은 재현 가능한 원본 로그와 named-layer 열거 증거가 없어 철회한다.

- 현재 08 registry에는 primary 호환 행 54개가 있다. `esri_reference` 6행은 제공 경로·SHA·WMS URL을 비운 차단 표식자이므로 서빙 가능 레이어로 세지 않는다.
- secondary 18개는 실제 실행된 모델 예측·confidence·valid mask provenance가 없다.
- 기존 secondary raster 생성 코드는 WorldCover/label 복제, 임의 confidence, 거의 전유효 mask를 만들었으므로 모델 추론 증거가 아니다.
- GetCapabilities HTTP 200과 표본 GetMap PNG 200은 서비스 응답 확인이며 전수 layer 게시나 픽셀 과학 정확도를 증명하지 않는다.

## 현재 증거 수치

| 항목 | 현재 값 | 상태 |
|---|---:|---|
| primary 로컬 TIFF 물리 존재 | 54 | 파일 존재만 확인 |
| primary registry에 경로/SHA가 인정된 행 | 48 | `LOCAL_FILE_SHA_VERIFIED_PROVENANCE_UNVERIFIED` 또는 `TESTED_SYNTHETIC` |
| WorldCover LUT가 Esri로 잘못 명명된 legacy 파일 | 6 | `BLOCKED_LEGACY_WORLDCOVER_CROSSWALK_QUARANTINED` |
| 그중 알려진 합성 coverage/recovery/missing fixture | 18 | `TESTED_SYNTHETIC` |
| secondary 실제 모델 출력으로 검증된 파일 | 0 | `BLOCKED` |
| capabilities 원문으로 전수 열거된 named layer | 0 | `BLOCKED` |
| 재현 가능한 원본-vs-WMS 픽셀 대조 | 0 | `BLOCKED` |
| 측정 가능한 T1/T2 변화·면적·탄소·파편화 통계 | 0 | `BLOCKED` |

## fail-closed 계약

`GeoServerSecondaryAndChangeManager`는 이제 raster를 생성하거나 GeoServer에 게시하지 않는다. 별도 inference evidence manifest가 없으면 6개 주 × 3종 secondary record를 모두 `BLOCKED`로 반환하며 파일 경로, SHA, CRS, 크기, nodata, 게시 상태와 WMS URL은 null이다.

`GeoServerPrimaryLayersManager`는 WorldCover를 LUT로 변환해 `esri_reference.tif`를 만들던 경로를 폐기했다. 기존 6개 파일이 남아 있어도 registry/manifest의 경로·WMS URL은 null/공란이고, `/geoserver/wms` 및 `/v1/lcluc/pixel`에서 해당 명을 요청하면 `409 UNVERIFIED_REFERENCE_PROVENANCE`을 반환한다. 실제 Esri 연차 자료는 권위 `annual-window-report.json`의 weak-label 레지스트리로만 조회하고, API에 `independent_ground_truth=false`, `model_prediction=false`를 명시한다.

manifest를 제공해도 다음 조건을 모두 통과해야 로컬 secondary artifact를 `VERIFIED_REAL`로 표시한다.

1. 실행 모델과 data root 내부 checkpoint/input 상대경로 및 실제 파일 SHA
2. confidence가 모델 softmax 최대확률에서 생성되었다는 provenance
3. valid mask가 inference 입력 mask에서 생성되었다는 provenance
4. 세 raster의 실제 파일 SHA와 동일 grid
5. class/confidence/mask 값 범위
6. prediction이 WorldCover reference와 byte 또는 pixel 단위로 동일하지 않음

로컬 파일 검증과 게시 검증은 별도다. data root 내부 GetCapabilities XML 원문, 실제 원문 SHA, XML에서 직접 파싱한 기대 secondary named layer 3종 열거가 모두 있어야 `VERIFIED_NAMED_LAYER_ENUMERATION`이 된다. manifest 내부 문자열 목록만으로 게시를 주장할 수 없다. 이 경우에도 이 모듈은 GetMap 성공이나 픽셀 일치를 자동 주장하지 않는다.

T1/T2 실제 예측·공통 valid mask·동일 grid·면적 산식이 검증되기 전 `compute_annual_changes()`는 모든 변화·탄소·생물다양성 값을 null로 둔다.
