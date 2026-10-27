# Unit 362 — 6개 주 경계 후보·GISTARU 서비스 탐색·36셀 SCL mosaic

> 2026-10-27 Unit 363 후속: GISTARU는 사용자 결정으로 provisional pilot 범위에서 생략했다. BIG 경계는 여전히 승인 대기이며, 실 Sentinel-2 SCL 1건을 추가해 121 source/updated mosaic로 갱신한 현재 근거는 `363_provisional_sentinel_pilot.md`다. 본 문서 아래의 120 source·GISTARU 차단 수치는 Unit 362 시점 이력으로 유지한다.

- 기준 시각: 2026-10-27 15:29 KST
- 전체 판정: **PARTIAL / BLOCKED_GISTARU_AND_BOUNDARY_APPROVAL**
- 신규 Sentinel-2 다운로드·collector·ledger write·execution lock·학습: **각 0**

## 1. 결론

사용자가 진행을 지시한 세 항목을 하나의 증거 bundle로 구현했다. 다만 경계의 현행 법적·통계 승인과 GISTARU live metadata는 확인하지 못했으므로 planner의 `VERIFIED_REAL` Gate를 열지 않는다.

| 요구 항목 | 실제 결과 | 상태 |
|---|---|---|
| 최신 6주 권위 경계 | BIG 공식 공개 MapServer layer 12의 6주 129개 원본 feature를 주별 dissolve하고 원응답·query·SHA를 고정 | `IMPLEMENTED_UNVERIFIED`, 관할 기관·통계 승인 대기 |
| GISTARU URL/layer/query/metadata | Java·Sulawesi 정확 MapServer 후보 URL 2개를 고정 | 현 host에서 DNS/HTTP 실패. layer id/name/query/metadata는 null, `BLOCKED` |
| 36셀 observed/cause mosaic | 보존된 실 `raw-SCL.tif` 120개를 사용해 6주×6년, 72개 GeoTIFF 생성 | 로컬 artifact 범위 `VERIFIED_REAL`, 경계 승인 대기 |

## 2. BIG 6주 경계 후보

사용 서비스는 BIG `BATASWILAYAH/BATAS_WILAYAH/MapServer/12`, layer name `Area Batas Wilayah Administrasi Provinsi`, EPSG:4326 polygon이다.

- Banten: 8 feature
- Jawa Barat: 27 feature
- Jawa Timur: 40 feature
- Sulawesi Selatan: 25 feature
- Gorontalo: 6 feature
- Sulawesi Tenggara: 23 feature

각 주를 `wadmpr='<local name>'`, `outSR=4326`, `f=geojson`으로 질의했고 원 응답을 `raw-boundary/`에 보존했다. 계산용 geometry는 주별 dissolve이며 서비스 원본과 파생물을 구분한다.

공개 layer metadata에서 2026-10-27 현재 효력일, 법적 승인 번호, 프로젝트 통계 사용 승인을 확인하지 못했다. 따라서 `approved_for_project_statistics=false`이며 경계를 planner의 권위 입력으로 승격시키지 않았다.

## 3. GISTARU 탐색

공식 서비스 catalog 후보에서 대상 주를 덮는 다음 URL을 고정했다.

1. `https://gistaru.atrbpn.go.id/arcgis/rest/services/004_RTR_PROVINSI_PULAU_JAWA/_3000_PROVINSI_JAWA_PR_PERDA/MapServer`
2. `https://gistaru.atrbpn.go.id/arcgis/rest/services/006_RTR_PROVINSI_PULAU_SULAWESI/_7000_PROVINSI_SULAWESI_PR_PERDA/MapServer`

현 실행 host에서 `gistaru.atrbpn.go.id` DNS 해석이 `getaddrinfo failed`ub85c 종료됐고, 검색으로 확인한 고정 IP 직접 연결도 timeout이었다. 서비스 metadata를 읽지 못했으므로 layer id/name, `query_where`, query response, BIG 경계와의 비교 결과를 임의로 채우지 않았다.

## 4. 36셀 EPSG:6933 SCL mosaic

`data/first-group-training-esri-v1/sources` 아래의 `raw-SCL.tif` 120개는 36개 주·연도 셀을 모두 포함한다. 셀당 2~7개 자산을 1 km equal-area inventory grid에 nearest-neighbor로 투영했다.

- observed=1: SCL 4, 5, 6, 7, 11이 하나라도 있음
- CLOUD: SCL 8, 9, 10
- SHADOW: SCL 2, 3
- NODATA: SCL 0, 1
- OUTSIDE_FOOTPRINT: 보존된 로컬 SCL 창이 없음
- 복수 관측 규칙: clear 하나라도 있으면 observed. 그 외은 다수 원인, 동률은 cloud → shadow → nodata.

전수 검산 결과는 다음과 같다.

| 항목 | 값 |
|---|---:|
| 전체 경계 pixel | 1,123,578 |
| observed | 10,032 (0.892862%) |
| gap | 1,113,546 |
| CLOUD | 607 |
| SHADOW | 374 |
| NODATA | 0 |
| OUTSIDE_FOOTPRINT | 1,112,565 |

`OUTSIDE_FOOTPRINT`가 압도적이므로 나머지를 구름으로 해석하면 안 된다. 1 km 결과는 공백 우선순위용 inventory이며 최종 10/20 m 과학 product가 아니다.

## 5. 구현·검증

- 구현: `backend/app/ml/province_year_evidence_builder.py`
- 생성 CLI: `scripts/build_province_year_evidence.py`
- 전수 검증 CLI: `scripts/validate_province_year_evidence.py`
- 시험: `tests/test_province_year_evidence_builder.py`
- 증거: `evidence/integration/unit362-province-evidence-20261027/`

검증 결과:

- 신규+기존 planner/coverage 회귀: **25 PASS / 102 warnings / 71.27초**
- Python compileall: PASS
- `git diff --check`: PASS
- 실산출물 재개방 검산: 36셀, 120 unique SCL, 72 GeoTIFF SHA 일치
- EPSG:6933, 셀별 observed/cause 동일 grid, nodata unset, 값 범위, 경계 밖 0, 미분류 gap 0: 전부 PASS

## 6. 다음 Gate

1. BIG/관할기관에서 현행 효력일·법적 공고·통계 사용 승인을 받고 경계 SHA를 재고정한다.
2. GISTARU가 접근 가능한 네트워크에서 두 MapServer metadata와 대상 layer/query 응답을 고정한다.
3. GISTARU geometry와 BIG 경계 차이를 실측하고 `VERIFIED_MATCH` 또는 승인된 차이 판정을 받는다.
4. 승인 경계로 36 mosaic를 재생성한 후 planner source/gistaru manifest를 고정한다.
5. 현 1 km inventory로 수집 후보를 검토하고, 승인된 수집 후 최종 해상도 mosaic와 QA를 별도 생성한다.

위 세 가지 외부 증거가 없으면 `BLOCKED_MISSING_AUTHORITATIVE_BOUNDARY_AND_CAUSE_MOSAICS`를 해제하지 않는다.

## 7. 로컬 재구동 확인

2026-10-27 사용자 요청으로 API `127.0.0.1:8002`, UI `127.0.0.1:5174`, GeoServer 호환 서비스 `127.0.0.1:8088`을 시작했다. `/api/health`, UI 루트, UI→API proxy, WMS GetCapabilities가 모두 실제 HTTP 200을 반환했다. 이 항목은 로컬 조회 서비스 재구동 근거이며 경계 승인, GISTARU 해제, 신규 Sentinel 수집, 학습 또는 운영 배포 근거가 아니다.
