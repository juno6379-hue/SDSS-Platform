# Unit 361 — 주 전체 누락 보완과 재학습 증거 파이프라인

- 상태: **IMPLEMENTED_UNVERIFIED / BLOCKED**
- 적용일: 2026-10-21
- 기준 커밋: `375f037379ac878353b652591d87a17efa51f021` 이후 작업 트리
- 실제 추가 수집·학습·예측·승격·배포: **각 0건**

## 1. 목적

주 전체 관측 공백을 보완하는 작업을 단순 다운로드로 끝내지 않고, 다음 MLOps 단계가 같은 증거를 사용하도록 연결한다.

1. 권위 경계와 GISTARU 교차검증
2. Sentinel-2/SCL 기반 공백 원인 측정
3. 수집 후보 계획과 별도 실행 승인
4. 수집 자료 QA 및 불변 데이터셋 pin
5. 재학습 run과 checkpoint 보존
6. 실제 예측과 confidence calibration
7. 독립 정답 기반 정확도 평가
8. 사람 승인
9. 모델 승격·배포와 rollback

현재는 1단계의 필수 입력인 권위 경계와 36개 동일 격자 observed/cause mosaic가 없으므로 전체 흐름을 fail-closed로 차단한다.

## 2. 자료별 역할

| 자료 | 허용 역할 | 금지 역할 |
|---|---|---|
| 권위 행정경계 | 통계 AOI와 면적 분모 | 위성 관측·토지피복 라벨 |
| GISTARU | 경계·공간계획 교차검증 | 단독 권위 경계, 위성 관측, 모델 정답 |
| Esri 연차 Land Cover | 학습·비교용 weak label | 독립 지상정답, Sentinel 관측 대체 |
| Sentinel-2 L2A | 실제 분광 관측 | 법적 경계·정확도 정답 |
| Sentinel-2 SCL | 구름·그림자 등 품질 원인 | 토지피복 정답 |

GISTARU 참조는 정확한 HTTPS MapServer URL, layer id/name, query, `outSR=4326`, 조회시각과 고정된 서비스 메타데이터·경계 비교 증거가 모두 있어야 통과한다. 공개 포털 주소만으로는 통과하지 않는다.

## 3. 구현

### 수집계획

`backend/app/ml/province_year_gap_acquisition_planner.py`는 6개 주 × 2020–2025년의 정확한 36개 셀을 요구한다. 각 셀은 EPSG:6933의 동일 격자 observed mask와 cause mask를 가져야 하며, 모든 공백 화소는 다음 원인 중 하나로 설명돼야 한다.

- `CLOUD`
- `SHADOW`
- `NODATA`
- `OUTSIDE_FOOTPRINT`

출력은 다운로드 요청이 아니라 `PLAN_CANDIDATE_ONLY` polygon이다. collector 호출, 원장 쓰기, lock 획득, 원격 다운로드는 모두 `false`로 고정된다. 필수 근거가 하나라도 없으면 target을 일부라도 만들지 않는다.

### API

`GET /v1/mlops/summary`의 스키마를 `2.1`로 올리고 `retraining_readiness` 계약을 추가했다. 다음 9단계를 각각 완료·차단 사유와 함께 반환한다.

1. `gap_measurement`
2. `collection_execution`
3. `dataset_freeze`
4. `training`
5. `prediction`
6. `confidence_calibration`
7. `independent_accuracy`
8. `human_approval`
9. `promotion_and_deployment`

현재 `pipeline_complete=false`, `retrain_allowed=false`다. confidence는 모델 확률의 보정 상태이고 accuracy가 아니다. 실제 calibration set, ECE, Brier score, reliability bin 근거가 없으므로 값은 null이다. OA/F1/mIoU도 독립 정답과 실제 예측이 없으므로 null이다.

### UI

`frontend/src/ModelMlopsWorkspace.tsx`는 위 9단계와 blocker를 표시한다. confidence와 독립 정확도를 별도 카드로 보여 주고, Esri weak label을 독립 정답으로 사용할 수 없음을 설명한다.

## 4. Esri 출처 P0 교정

로컬 `geoserver_layers/primary/*/esri_reference.tif` 6개는 픽셀 전수 비교에서 WorldCover LUT 변환물과 모두 정확히 일치했다. 따라서 실제 Esri 제품으로 인정하지 않는다.

- primary manifest 스키마: `3.2-esri-provenance-fail-closed`
- primary slot: 총 54
- 수용 가능한 primary artifact: 48
- 격리된 legacy Esri 명칭 파일: 6
- legacy WMS/pixel/direct path 조회: HTTP 409 `UNVERIFIED_REFERENCE_PROVENANCE`
- 실제 Esri 연차 자료: `weak_label_agreement`, `independent_ground_truth=false`, `model_prediction=false`

기존 물리 파일은 감사 증거로 보존하지만 registry path/SHA/WMS URL은 비워 게시 대상에서 제외한다.

## 5. 검증

- gap planner + coverage 집중 회귀: **21 passed**, 24 warnings, 21.31초
- Esri/GeoServer/API/MLOps 통합 부분 회귀: **59 passed**, 147 warnings, 2 subtests, 37.75초
- MLOps router 집중 회귀: **8 passed**, 1 warning, 8.40초
- UI 계약 시험: **1 passed**
- frontend build: **성공**, 131 modules
- Python compile 및 `git diff --check`: 통과
- Root 최종 통합 회귀: **80 passed**, 171 warnings, 2 subtests, 67.26초

실행 중 로컬 서비스에도 반영했다. API 8002 `/healthz`, UI 5174와 proxy health, GeoServer 호환 8088 GetCapabilities는 HTTP 200이었다. legacy `primary_esri_reference_banten_2021` GetMap은 HTTP 409였다. 실제 브라우저의 MLOps 화면에서 9개 단계가 모두 BLOCKED이고 confidence와 독립 accuracy/F1/mIoU가 미측정이며 재학습·승인 버튼이 차단된 것을 확인했다. 이는 로컬 UI 적용 검증이며 실제 모델 과학성이나 운영 배포 검증이 아니다.

위 시험은 코드 계약과 로컬 fixture를 검증한다. 실제 GISTARU 레이어 취득, Sentinel-2 추가 다운로드, 재학습, 예측, confidence calibration, 독립 정확도, 사람 승인, 운영 승격·배포를 검증한 것이 아니다.

## 6. 현재 차단 상태와 다음 Gate

현재 blocker는 `BLOCKED_MISSING_AUTHORITATIVE_BOUNDARY_AND_CAUSE_MOSAICS`다. 다음 순서로만 진행할 수 있다.

1. 권위 행정경계와 GISTARU의 정확한 서비스·레이어 메타데이터를 고정한다.
2. 36개 셀의 Sentinel-2/SCL 동일 격자 observed/cause mosaic를 만든다.
3. 계획기를 실행해 원인별 수집 후보를 산출하고 사람이 검토한다.
4. 예산·중복·전역 lock을 확인한 뒤 별도 승인된 수집을 실행한다.
5. 수집분 QA와 불변 dataset pin을 완료한다.
6. 지리·시간 분할 충돌과 클래스 gate를 해소한 뒤 재학습한다.
7. 실제 prediction으로 confidence를 보정하고 독립 정답으로 OA/F1/mIoU를 측정한다.
8. 사람 승인 뒤에만 승격·배포한다.

현재 원본 1,779행 중 품질 적격 1,407행(865/292/250), 원본 scene split conflict 1건, 클래스 조건 미달 때문에 `learning_ready=false`다.
