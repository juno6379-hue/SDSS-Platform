# Unit 361 — 6개 주 전역 결측 보완 수집 계획 계약

> 2026-10-27 Unit 363 후속 정책: 기존 승인 경계+GISTARU `VERIFIED_REAL` 경로는 보존하고, 사용자의 명시적 GISTARU 생략 결정·BIG 임시 경계 SHA·실 SCL mosaic pin에 결속된 `PROVISIONAL_REAL` **단일 pilot 전용** 경로를 추가했다. 대량 수집·학습·배포 Gate를 해제한 것이 아니다. 실행 근거는 `363_provisional_sentinel_pilot.md`다.

## 1. 상태와 목적

- 구현 상태: **IMPLEMENTED_UNVERIFIED**
- 자동시험 상태: **TESTED_SYNTHETIC**
- 실제 6개 주 계획 상태: **BLOCKED**
- 실제 수집, 원격 조회, 원장 기록, execution lock, 학습·배포: **0회**

이 단위는 6개 주의 2020~2025년 전체 행정구역에서 Sentinel-2 관측 결측을 보완하기 위한 **계획 파일만** 만든다. 현재 운영 자료는 권위 경계와 주 전역 동일 격자 observed/cause mosaic가 없으므로 실제 계획을 생성하지 않는다. 기존 1,779개 patch와 2021년 소형 GeoServer 예시를 주 전체 coverage로 확대하지 않는다.

## 2. 자료별 책임 분리

| 자료 | 허용 역할 | 금지 역할 |
|---|---|---|
| 권위 행정경계 | 통계 AOI와 주 내부 픽셀 판정 | 약라벨·관측 품질 판정 |
| GISTARU | 권위 경계와의 교차검증 증거 | 단독 법정 경계 확정, 구름·NoData 판정 |
| Esri 연례 LULC | 학습용 약라벨 참고 | gap 탐지, 경계 결정, 독립 정답 |
| Sentinel-2 L2A/SCL | observed와 cloud/shadow/NoData/outside 원인 mosaic | 행정경계·독립 토지피복 정답 |

입력의 `roles`는 아래 값과 정확히 같아야 한다.

```json
{
  "authoritative_boundary": "STATISTICAL_AOI_ONLY",
  "gistaru": "BOUNDARY_CROSS_CHECK_ONLY",
  "esri": "WEAK_LABEL_ONLY",
  "sentinel2": "OBSERVATION_AND_CAUSE_MASK_SOURCE"
}
```

`esri_used_for_gap_detection`와 `esri_used_for_boundary`는 반드시 `false`, `sentinel2_used_for_gap_detection`은 반드시 `true`다.

## 3. 입력 계약

### 3.1 권위 경계

경계 JSON은 `province-boundaries/1.0`, 명시적 `EPSG:4326`, 정확히 다음 6개 `province_id`를 포함한다.

`banten`, `west_java`, `east_java`, `south_sulawesi`, `gorontalo`, `southeast_sulawesi`

또한 다음 authority 증거가 필수다.

- `legal_status=AUTHORITATIVE_ADMINISTRATIVE_BOUNDARY`
- `approved_for_statistics=true`
- 비어 있지 않은 `organization`, `publication_id`
- ISO 8601 `effective_date`
- HTTPS `source_url`
- 파일 전체 SHA-256 고정

현재 `data/first-group-boundaries/selected-six.geojson`은 2017 geoBoundaries 참조이고 `boundary_is_current_legal_authority=false`이므로 이 계약을 통과하지 못한다.

### 3.2 GISTARU 교차검증

별도 `gistaru-boundary-reference/1.0` JSON을 SHA-256으로 고정한다. `portal_url`은 `https://gistaru.atrbpn.go.id`, 역할은 `BOUNDARY_CROSS_CHECK_ONLY`여야 한다. 정확한 ArcGIS REST `MapServer` URL, 0 이상의 layer ID, layer 이름, 실제 query 조건, `out_sr=4326`, 조회시각, SHA가 고정된 서비스 메타데이터 응답이 모두 필요하다. `comparison_status`는 `VERIFIED_MATCH` 또는 `DISCREPANCY_ADJUDICATED`만 허용하며, 로컬 비교 증거 파일의 경로와 SHA도 필수다. 공개 화면 주소나 RTR 서비스 이름만 기록한 경우는 차단한다.

GISTARU 비교는 법적 권한을 대신하지 않는다. 불일치가 있으면 책임기관 판정 근거를 남긴 뒤 `DISCREPANCY_ADJUDICATED`로 입력해야 한다.

### 3.3 Sentinel-2와 Esri provenance

Sentinel provenance는 `sentinel-2-observation-provenance/1.0`, collection `sentinel-2-l2a`, `scl_used_for_cause=true`여야 한다. `VERIFIED_REAL` 입력은 `observations_verified=true`를 추가로 요구한다. 합성시험은 `fixture_only=true`를 요구해 실제 자료로 오인하지 못하게 한다.

Esri provenance는 `esri-weak-label-provenance/1.0`이며 `used_for_gap_detection=false`, `used_as_independent_ground_truth=false`여야 한다.

### 3.4 36개 동일 격자 mosaic

source JSON은 `province-year-gap-acquisition-source/1.0`이고 정확히 6주×2020~2025의 36개 셀을 한 번씩 포함한다. 각 셀은 SHA가 고정된 다음 두 단일 band GeoTIFF를 제공한다.

- observed: `BINARY_OBSERVED_0_1`, `quality-mask/1.0`
- cause: `0_NONE_1_CLOUD_2_SHADOW_3_NODATA_4_OUTSIDE_FOOTPRINT`, `acquisition-gap-cause-mask/1.0`

두 파일은 동일한 EPSG:6933 CRS·shape·affine grid를 가져야 하고 raster NoData는 설정하지 않는다. 주 경계 밖 값은 모두 0이어야 한다. 주 내부에서 observed=1이면 cause=0, observed=0이면 cause는 반드시 1~4 중 하나여야 한다. 원인이 0인 결측 픽셀은 `UNCLASSIFIED_GAP_PIXEL`로 전체 계획을 차단한다.

## 4. 출력 계약

`build_gap_acquisition_plan()`은 **모든 36개 셀과 모든 SHA·grid·pixel 의미를 먼저 검증한 뒤** target을 만든다. 한 셀이라도 실패하면 target 0개 상태로 예외를 반환한다.

성공 결과는 `province-year-gap-acquisition-plan/1.1`이며 다음 안전 필드를 고정한다.

- `execution_authorized=false`
- `collector_invoked=false`
- `ledger_written=false`
- `execution_lock_acquired=false`
- `remote_downloads_performed=false`
- target별 `remote_request_created=false`

target은 cause별 연결 영역의 WGS84 geometry/bbox, equal-area 픽셀 면적 기반 ha, 원인, 우선순위만 담는다. 우선순위는 `OUTSIDE_FOOTPRINT → NODATA → CLOUD → SHADOW`다. 이것은 후보 AOI이며 승인·다운로드 요청이 아니다.

### 4.1 MLOps 인계 Gate

출력의 `mlops_handoff`는 다음 순서를 구조화한다.

1. `coverage_boundary_cause_evidence`: 권위 경계와 동일 격자 observed/cause 증거
2. `acquisition_execution`: 승인된 collector 실행 manifest와 취득 asset SHA
3. `acquisition_quality_qa`: coverage·SCL·grid·NoData·source lineage 독립 QA
4. `immutable_dataset_pin`: 승인 asset과 split을 모두 고정한 불변 dataset manifest
5. `retraining_readiness`: 선행 Gate 전부 통과와 명시적 학습 승인

planner 성공 직후에도 2~5는 실행되지 않았으므로 상태는 `BLOCKED_PENDING_ACQUISITION_AND_DATASET_PIN`, `retraining_ready=false`, `immutable_dataset_pin=null`이다. 합성 fixture에서는 1번도 `TESTED_SYNTHETIC`이며 `PASSED`가 아니다. 따라서 데이터 준비 전 재학습 Gate가 열리지 않는다.

## 5. Python API

```python
from pathlib import Path
from app.ml.province_year_coverage import PinnedFile
from app.ml.province_year_gap_acquisition_planner import build_gap_acquisition_plan

plan = build_gap_acquisition_plan(
    root=Path("validated-input-root"),
    source=PinnedFile(Path("source.json"), "<64-char-sha256>"),
    boundaries=PinnedFile(Path("boundaries.geojson"), "<64-char-sha256>"),
    gistaru_reference=PinnedFile(Path("gistaru-reference.json"), "<64-char-sha256>"),
    evidence_status="VERIFIED_REAL",
)
```

## 6. CLI

```powershell
python scripts/plan_province_year_gap_acquisition.py `
  --root <validated-input-root> `
  --source <source.json> --source-sha256 <sha256> `
  --boundaries <boundaries.geojson> --boundaries-sha256 <sha256> `
  --gistaru-reference <gistaru-reference.json> `
  --gistaru-reference-sha256 <sha256> `
  --output <new-plan.json> --evidence-status VERIFIED_REAL
```

차단 시 종료코드 2와 `output_written=false`를 stderr JSON으로 반환하며 출력 파일을 만들지 않는다. 성공 파일도 exclusive create를 사용해 기존 증거를 덮어쓰지 않는다.

## 7. 시험 근거

`tests/test_province_year_gap_acquisition_planner.py`는 다음을 검증한다.

1. 36셀 합성 fixture에서 4종 원인 target과 비실행 플래그 생성
2. 비권위 경계 차단
3. 미검증 GISTARU 비교와 exact service/layer metadata 부재 차단
4. Esri 약라벨을 gap 근거로 승격하는 입력 차단
5. observed/cause grid 불일치 차단
6. 원인 미분류 gap 픽셀 차단
7. 36셀 누락 차단
8. SHA 불일치 차단
9. CLI 성공 후 새 파일 생성과 덮어쓰기 거부
10. CLI 실패 시 출력 0
11. 수집 실행·QA·불변 dataset pin 전 `retraining_ready=false`와 후속 Gate 차단
12. 입력 파일 부재를 명시적 fail-closed 증거 오류로 변환

집중 회귀 명령은 다음과 같다.

```powershell
python -m pytest tests/test_province_year_gap_acquisition_planner.py tests/test_province_year_coverage.py -q
```

작업자 기준 결과는 **20 PASS / 0 FAIL / 23 warnings / 22.01초**다. Root가 GISTARU exact service/layer fail-closed 사례를 추가한 최종 집중 회귀는 **21 PASS / 0 FAIL / 24 warnings / 21.31초**다. warning은 rasterio affine 곱셈의 PendingDeprecationWarning이며 기능 실패가 아니다. 작업자 원문은 `evidence/integration/unit361-gap-acquisition-planner-20261021/pytest.log`, 요약과 불변 SHA는 같은 디렉터리의 `completion.json`에 있다. Root 최종 결과는 Unit361 통합 근거에 기록한다.

## 8. 현재 차단 조건과 후속 Gate

현재 운영 데이터로 실행하면 다음 증거가 없으므로 실제 target manifest를 만들 수 없다.

- 통계 사용 승인된 최신 6주 법정 경계
- 경계 SHA에 결속된 GISTARU 비교 증거
- 36개 셀 전체의 Sentinel-2/SCL 기반 EPSG:6933 observed/cause mosaic
- 원인 미분류 0과 주 경계 밖 비정상 픽셀 0 검증

후속 단계는 책임기관 경계 확보와 GISTARU 비교, Sentinel-2 mosaic 생성·독립 감사다. 그 뒤 이 planner가 만든 `PLANNED_NO_EXECUTION` manifest를 사람이 검토해야 한다. 수집 실행에는 별도 예산·원장·전역 lock·승인 Gate가 필요하며 이 단위는 해당 기능을 포함하지 않는다.

## 9. UI와 이해자료 영향

신규 API endpoint나 화면 연결은 없다. 따라서 실행 중 UI 영향은 0이다. Root가 구현을 통합한 뒤 Understanding Agent가 쉬운 설명·시험 증거·발표 대본·FAQ·INDEX를 별도 갱신해야 한다.
